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
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*)  FILE_LANG=de DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN)

fr_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*) FILE_LANG=fr DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN)

it_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_ALIGN)/,,$*) FILE_LANG=it DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_ALIGN)



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
	> $@  \
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

de-fr-alignments-stats-target: $(de-fr-alignments-stats-files)

de_fr_overview_stats_alignment.csv: $(de-fr-alignments-stats-files)
	head -1 $< > $<.header.temp
	awk 'FNR > 1' $^ > $@.temp
	cat $<.header.temp $@.temp > $@
	rm $<.header.temp $@.temp

#### SENTENCE ALIGMNENT ###

# Firstly, remove first and last line from the translation file.
# Secondly, split this file into its articles at .EOA delimiter and write into RAM.
# Thirdly, rename all article according to its first line
# Fourthly, remove first line in all files which contains the file name

de-fr-translated-dummy:=$(patsubst %, $(DIR_ALIGN)/de_fr_%_trans_dummy.txt, $(YEARS))

de_fr_%_trans_dummy.txt: de_fr_%_all.txt
	mkdir -p $(DIR_TRANS)/$*
	sed '1d; $d' $< | csplit -z --digits=4 --quiet --suppress-matched --prefix=$(DIR_TRANS)/$*/trans_art /dev/stdin "/.EOA/" "{*}"
	for i in "$(DIR_TRANS)/$*/"trans_art*; do mv -n "$$i" "$(DIR_TRANS)/$*/$$(basename $$(cat "$$i"|head -n1))"; done
	sed -i '1d' "$(DIR_TRANS)/$*/"*.cuttered.sent.txt


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
	while IFS=$$'\t' read -r col_src col_trg col_trans ; do  bleu-champ -q -s $${col_trans} -t $${col_trg} -S $${col_src} >> $@ ; echo '.EOA' >> $@; done < $<
	rm -r "$(DIR_TRANS)/$*"


# Create a parallel corpus across years as tsv file
$(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv: $(de-fr-parallel-corpus-files)
	cat > $@


# Split the parallel corpus into separate files per language
all_sent_parallel-target: $(DIR_ALIGN)/de_fr_sent_parallel_de.txt $(DIR_ALIGN)/de_fr_sent_parallel_fr.txt

$(DIR_ALIGN)/de_fr_sent_parallel.de: $(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv
	cut -f1 $< > $@

$(DIR_ALIGN)/de_fr_sent_parallel.fr: $(DIR_ALIGN)/de_fr_all_parallel_corpus.tsv
	cut -f2 $< > $@


#### MULTILINGUAL EMBEDDINGS ###
DIR_EMBED?= embedding
DIR_EMBED_DATA?= embedding/data

all_sent_parallel-target: $(DIR_EMBED)/vectors.de-fr.de.vec $(DIR_EMBED)/vectors.de-fr.fr.vec

# Prepare data
$(DIR_EMBED_DATA)/de_fr_sent_parallel_clean.de: $(DIR_ALIGN)/de_fr_sent_parallel.de $(DIR_ALIGN)/de_fr_sent_parallel.fr
	python2 lib/multivec_scripts/prepare-data.py $(<:.de=) $(@:.de=) de fr \
	--lowercase --normalize-digits --normalize-punk --min-count 10 --shuffle --script lib/multivec_scripts --threads 4 --verbose
$(DIR_EMBED_DATA)/de_fr_sent_parallel_clean.fr: $(DIR_EMBED_DATA)/de_fr_sent_parallel_clean.de

# Train multivec models
$(DIR_EMBED)/biskip.de-fr.bin: $(DIR_EMBED_DATA)/de_fr_sent_parallel_clean.de $(DIR_EMBED_DATA)/de_fr_sent_parallel_clean.fr
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 100 --min-count 10 --window-size 5 --threads 10 --iter 10 --sg --save $@

$(DIR_EMBED)/biskip.de-fr.de.bin: $(DIR_EMBED)/biskip.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.de-fr.fr.bin: $(DIR_EMBED)/biskip.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.de-fr.de.vec: $(DIR_EMBED)/biskip.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.de-fr.fr.vec: $(DIR_EMBED)/biskip.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@
