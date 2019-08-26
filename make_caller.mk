SHELL:=/bin/bash

# ensure that entire pipe command fails if a part fails
export SHELLOPTS:=errexit:pipefail


DIR_IN?= data_text
DIR_ALIGN?= data_alignment
DIR_TRANS?= /dev/shm/impresso

YEARS_START?= 1850
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 1 $(YEARS_END))



# debug print content of variable
print-%: ; @echo $* is $($*)

#### TOKENIZING ###
# segment and tokenize extracted text data anually and merge into single document

de-single-doc-files:=$(patsubst %, $(DIR_ALIGN)/de_%_all.txt, $(YEARS))
fr-single-doc-files:=$(patsubst %, $(DIR_ALIGN)/fr_%_all.txt, $(YEARS))
it-single-doc-files:=$(patsubst %, $(DIR_ALIGN)/it_%_all.txt, $(YEARS))

de-single-doc-target: $(de-single-doc-files)
fr-single-doc-target: $(fr-single-doc-files)
it-single-doc-target: $(it-single-doc-files)

all-single-doc-target: de-single-doc-target fr-single-doc-target it-single-doc-target

de_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*) FILE_LANG=de DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN) single-doc-year-target

fr_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*) FILE_LANG=fr DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN) single-doc-year-target

it_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*) FILE_LANG=it DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN) single-doc-year-target



#### DOCUMENT ALIGMNENT ###

de-fr-trans-doc-files:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_all.txt, $(YEARS))
de-it-trans-doc-files:=$(patsubst %, $(DIR_ALIGN)/de_it_%_all.txt, $(YEARS))

de-fr-trans-target: $(de-fr-trans-doc-files)
de-it-trans-target: $(de-it-trans-doc-files)

all-trans-target: de-fr-trans-target de-it-trans-target

# Translate the German doc into French and Italian with Moses
de_fr_%_all.txt: de_%_all.txt
	cat $< | \
	/mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/lowercase.perl | \
	perl /mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/escape-special-chars.perl | \
	moses -f mt_moses/train_de_fr/binarised_model/moses.ini -v 0 -threads 4 | \
	perl /mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/deescape-special-chars.perl | \
	sed -r "s/^\.eoa/.EOA/" \
	sed -r "s/^\.eob/.EOB/" \
	> $@ \
	|| echo 'Error during Moses translation process for the following year: ' $@ >> log_moses.txt

# TODO: translate documents from German to Italian
de_it_%_all.txt: de_%_all.txt

# Compute BLEU-alignments for German and French documents
de-fr-alignments-doc-files:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_alignments.xml, $(YEARS))

de-fr-alignments-doc-target: $(de-fr-alignments-doc-files)

de_fr_%_alignments.xml: de_%_all.txt fr_%_all.txt de_fr_%_all.txt
	python3 lib/bleualign_articles.py -src $(word 1, $^) -trg $(word 2, $^) \
	-t $(word 3, $^) -o $@ -c

# Collect the alignment stats per language pair and merge them into single csv

de-fr-alignments-stats-files:=$(de-fr-alignments-doc-files:.xml=_stats.csv)

de-fr-alignments-stats-target: $(de-fr-alignments-stats-files) $(DIR_ALIGN)/de_fr_overview_stats_alignment.csv

$(DIR_ALIGN)/de_fr_overview_stats_alignment.csv: $(de-fr-alignments-stats-files)
	head -1 $< > $<.header.temp
	awk 'FNR > 1' $^ > $@.temp
	cat $<.header.temp $@.temp > $@
	rm $<.header.temp $@.temp

#### SENTENCE ALIGMNENT ###

# Firstly, remove first and last line from the translation file (delimiter volume organization)
# Secondly, split this file into its articles at .EOA delimiter and write into RAM.
# Thirdly, rename all article according to its first line
# Fourthly, remove first line in all files which contains the file name

de-fr-translated-dummy:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_trans_dummy.txt, $(YEARS))

de_fr_%_trans_dummy.txt: de_fr_%_all.txt
	mkdir -p $(DIR_TRANS)/$*
	sed '1d; $$d' $< | csplit -z --digits=4 --quiet --suppress-matched --prefix=$(DIR_TRANS)/$*/trans_art /dev/stdin "/.EOA/" "{*}"
	for i in "$(DIR_TRANS)/$*/"trans_art*; do mv "$$i" "$(DIR_TRANS)/$*/$$(basename $$(cat "$$i"|head -n1))"; done
	sed -i '1d' "$(DIR_TRANS)/$*/"*.cuttered.sent.txt || echo 'Error during pre-processing for the following year: ' $@ >> log_dummy_trans.txt


# Create a tsv-file with all aligned articles (src, trg, translation)
de-fr-aligned-doc-files:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_aligned_docs.tsv, $(YEARS))

de-fr-aligned-doc-target: $(de-fr-aligned-doc-files)

de_fr_%_aligned_docs.tsv: de_fr_%_alignments.xml de_fr_%_trans_dummy.txt
	python lib/aligned2tsv.py -i $< -o $@ -t $(DIR_TRANS)/$(DIR_ALIGN)


# Align sentences with bleu-champ and set EOA-marker to indicate the article boundaries
# After the alignment, clean up directory with translated files
de-fr-parallel-corpus-files:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_parallel_corpus.tsv, $(YEARS))
de-fr-parallel-corpus-target: $(de-fr-parallel-corpus-files)

de_fr_%_parallel_corpus.tsv: de_fr_%_aligned_docs.tsv
	while IFS=$$'\t' read -r col_src col_trg col_trans ; do bleu-champ -q -s $${col_trans} -t $${col_trg} -S $${col_src} >> $@ ; echo '.EOA\t.EOA' >> $@; done < $<
#	rm -r "$(DIR_TRANS)/$*"


# Create a parallel corpus across years as tsv file
$(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv: $(de-fr-parallel-corpus-files)
	cat $^ > $@


# Split the parallel corpus into separate files per language
$(DIR_ALIGN)/de_fr_sent_parallel.de: $(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv
	cut -f1 $< > $@

$(DIR_ALIGN)/de_fr_sent_parallel.fr: $(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv
	cut -f2 $< > $@

# Filter the parallel corpus. Only keeping sentences with a length between 20 and 600.
$(DIR_ALIGN)/de_fr_sent_parallel_filtered.de: $(DIR_ALIGN)/de_fr_sent_parallel.de $(DIR_ALIGN)/de_fr_sent_parallel.fr
	/mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/training/clean-corpus-n.perl \
	$(<:.de=) de fr $(@:.de=) 20 600
$(DIR_ALIGN)/de_fr_sent_parallel_filtered.fr: $(DIR_ALIGN)/de_fr_sent_parallel_filtered.de



#### MULTILINGUAL EMBEDDINGS ###
DIR_EMBED?= embedding
DIR_EMBED_DATA?= embedding/data
DIR_EUROPARL?= europarl_data

# Tokenize Europarl corpus (perl command to retrieve line-based structure)
europarl-de-fr-files: $(DIR_EUROPARL)/Europarl.de-fr.de $(DIR_EUROPARL)/Europarl.de-fr.fr
europarl-de-fr-cuttered-files:= $(DIR_EUROPARL)/Europarl.de-fr.cuttered.de $(DIR_EUROPARL)/Europarl.de-fr.cuttered.fr
europarl-de-fr-cuttered-target: $(europarl-de-fr-cuttered-files)

Europarl.de-fr.cuttered.%: Europarl.de-fr.%
	cat $< | cutter $(*F) -T | perl -p -e "s/(?<=.)\n/ /g" | sed "/^$$/d" > $@

# Merge with EuroParl corpus
de_fr_parallel_fedgaz_europarl-files:= $(DIR_EMBED_DATA)/de_fr_parallel_fedgaz_europarl.de $(DIR_EMBED_DATA)/de_fr_parallel_fedgaz_europarl.fr
# TODO: weirdly, here the dir is needed, otherwise the target rule is not found
#de_fr_parallel_fedgaz_europarl.%: de_fr_sent_parallel_filtered.% Europarl.de-fr.cuttered.%
$(DIR_EMBED_DATA)/de_fr_parallel_fedgaz_europarl.%: $(DIR_ALIGN)/de_fr_sent_parallel_filtered.% $(DIR_EUROPARL)/Europarl.de-fr.cuttered.%
	cat $^ > $@

# Prepare data (French is cleaned implicitly)
de-fr-sent-parallel-clean-de-files:=$(DIR_EMBED_DATA)/de_fr_parallel_clean.de
de-fr-sent-parallel-clean-fr-files:=$(DIR_EMBED_DATA)/de_fr_parallel_clean.fr
de-fr-sent-parallel-clean-files:= $(de-fr-sent-parallel-clean-de-files) $(de-fr-sent-parallel-clean-fr-files)

$(de-fr-sent-parallel-clean-de-files): $(de_fr_parallel_fedgaz_europarl-files)
	python2 lib/multivec_scripts/prepare-data.py $(<:.de=) $(@:.de=) de fr \
	--lowercase --normalize-digits --min-count 5 --shuffle --script lib/multivec_scripts --threads 10 --verbose
$(de-fr-sent-parallel-clean-fr-files): $(de_fr_parallel_fedgaz_europarl-files)

# keep only alpha-numeric character, underscore, and hyphen
de-fr-sent-parallel-clean-nopunc-files:= $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.de $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.fr

# remove all special characters if preceded by a initial space (i.e. if they are a token)
de_fr_parallel_clean_nopunc.%: de_fr_parallel_clean.%
	cat $< | sed "s/ [^[:alnum:] \_-]\+/ /g" | sed "s/ \+/ /g" > $@

de-fr-prepare-embedding-data-target: $(de-fr-sent-parallel-clean-nopunc-files) $(de_fr_parallel_fedgaz_europarl-files)

# Train multivec models with dimension 100
vectors-100-de-fr-target: $(DIR_EMBED)/vectors.100.de-fr.de.vec $(DIR_EMBED)/vectors.100.de-fr.fr.vec $(DIR_EMBED)/vectors.100.de-fr.de.eval.txt

$(DIR_EMBED)/biskip.100.de-fr.bin: $(de-fr-sent-parallel-clean-nopunc-files)
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 100 --min-count 10 --window-size 10 --threads 10 --iter 20 --sg --save $@

$(DIR_EMBED)/biskip.100.de-fr.de.bin: $(DIR_EMBED)/biskip.100.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.100.de-fr.fr.bin: $(DIR_EMBED)/biskip.100.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.100.de-fr.de.vec: $(DIR_EMBED)/biskip.100.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.100.de-fr.fr.vec: $(DIR_EMBED)/biskip.100.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.100.de-fr.de.eval.txt: $(DIR_EMBED)/vectors.100.de-fr.de.vec
	python3 lib/eval_embeddings.py $< --lowercase &> $@

# Train and evaluate multivec models with dimension 300
vectors-300-de-fr-target: $(DIR_EMBED)/vectors.300.de-fr.de.vec $(DIR_EMBED)/vectors.300.de-fr.fr.vec $(DIR_EMBED)/vectors.300.de-fr.de.eval.txt

$(DIR_EMBED)/biskip.300.de-fr.bin: $(de-fr-sent-parallel-clean-nopunc-files)
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 300 --min-count 10 --window-size 10 --threads 10 --iter 20 --sg --save $@

$(DIR_EMBED)/biskip.300.de-fr.de.bin: $(DIR_EMBED)/biskip.300.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.300.de-fr.fr.bin: $(DIR_EMBED)/biskip.300.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.300.de-fr.de.vec: $(DIR_EMBED)/biskip.300.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.300.de-fr.fr.vec: $(DIR_EMBED)/biskip.300.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.300.de-fr.de.eval.txt: $(DIR_EMBED)/vectors.300.de-fr.de.vec
	python3 lib/eval_embeddings.py $< --lowercase &> $@

vectors-all-de-fr-target: vectors-100-de-fr-target vectors-300-de-fr-target
