SHELL:=/bin/bash


DIR_IN?= data_text
DIR_OUT?= data_alignment
DIR_TRANS?= /dev/shm/impresso

YEARS_START?= 1850
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 20 $(YEARS_END))

de-fr-trans-doc-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_all.txt, $(YEARS))
de-fr-alignments-doc-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_alignments.xml, $(YEARS))
de-fr-aligned-doc-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_aligned_docs.tsv, $(YEARS))
de-fr-parallel-corpus-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_parallel_corpus.txt, $(YEARS))

de-fr-translated-dummy:=$(patsubst %, $(DIR_OUT)/de_fr_%_trans_dummy.txt, $(YEARS))

de-fr-alignments-target: $(de-fr-trans-files) $(de-fr-alignments-doc-files) $(de-fr-parallel-corpus-files) $(de-fr-aligned-doc-files)

print-%: ; @echo $* is $($*)

#### TOKENIZING ###
# segment and tokenize extracted text data anually and language-wise

# DE
de_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_OUT)/,,$*)  FILE_LANG=de DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_OUT)

# FR
fr_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_OUT)/,,$*) FILE_LANG=fr DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_OUT)

de-single-doc-files:=$(patsubst %, $(DIR_OUT)/de_%_all.txt, $(YEARS))
fr-single-doc-files:=$(patsubst %, $(DIR_OUT)/fr_%_all.txt, $(YEARS))

de-single-doc-target: $(de-single-doc-files)
fr-single-doc-target: $(fr-single-doc-files)

all-single-doc-target: de-single-doc-target fr-single-doc-target


#### DOCUMENT ALIGMNENT ###

# Translate all German docs to French with Moses
# Remove square brackets as Moses cannot process them
de_fr_%_all.txt: de_%_all.txt
	cat $< | \
	/mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/lowercase.perl | \
	sed -r "s/\[//g" | sed -r "s/\]//g" | \
	moses -f mt_moses/train_de_fr/binarised_model/moses.ini -v 0 -threads 5 | \
	sed -r "s/^\.eoa/.EOA/" \
	> $@

# Compute BLEU-alignments for German and French documents
de_fr_%_alignments.xml: de_%_all.txt fr_%_all.txt de_fr_%_all.txt
	python3 lib/bleualign_articles.py -src $(word 1, $^) -trg $(word 2, $^) \
	-t $(word 3, $^) -o $@ -c

# collect all alignment stats and merge them into single csv
de_fr_overview_stats_alignment.csv: #$(de-fr-alignments-doc-files) TODO: make proper dependencies de_fr_%_alignments.xml
	head -n 1 $(DIR_OUT)/*.csv |  sed '2q;d' > csv_header.txt
	awk 'FNR > 1' *.csv > total_stats_alignment.csv
	cat csv_header.txt total_stats_alignment.csv > $@
	rm csv_header.txt total_stats_alignment.csv

all_overview_stats_alignment-target: $(DIR_OUT)/de_fr_overview_stats_alignment.csv


#### SENTENCE ALIGMNENT ###

# Firstly, remove first and last line from the translation file.
# Secondly, split this file into its articles at .EOA delimiter and write into RAM.
# Thirdly, rename all article according to its first line
# Fourthly, remove first line in all files which contains the file name


de_fr_%_trans_dummy.txt: de_fr_%_all.txt
	mkdir -p $(DIR_TRANS)/$*
	sed '1d; $d' $< | csplit -z --digits=4 --quiet --suppress-matched --prefix=$(DIR_TRANS)/$*/trans_art /dev/stdin "/.EOA/" "{*}"
	for i in "$(DIR_TRANS)/$*/"trans_art*; do mv -n "$$i" "$(DIR_TRANS)/$*/$$(basename $$(cat "$$i"|head -n1))"; done
	sed -i '1d' "$(DIR_TRANS)/$*/"*.cuttered.sent.txt


# Create a tsv-file with all aligned articles (src, trg, translation)
de_fr_%_aligned_docs.tsv: de_fr_%_alignments.xml de_fr_%_trans_dummy.txt
	python lib/aligned2tsv.py -i $< -o $@ -t $(DIR_TRANS)/$(DIR_OUT)

# Align sentences with bleu-champ and set EOA-marker to indicate the article boundaries
# After the alignment, clean up directory with translated files
de_fr_%_parallel_corpus.txt: de_fr_%_aligned_docs.tsv
	while IFS=$$'\t' read -r col_src col_trg col_trans ; do  bleu-champ -q -s $${col_trans} -t $${col_trg} -S $${col_src} >> $@ ; echo 'EOA' >> $@; done < $<
	rm -r "$(DIR_TRANS)/$*"

# Create parallel corpus
$(DIR_OUT)/de_fr_all_parallel_corpus.txt: de_fr_%_parallel_corpus.txt
	cat $< | tr '[:upper:]' '[:lower:]' | tr '[0-9]' '0' > $@

$(DIR_OUT)/de_sent_parallel.txt: $(DIR_OUT)/de_fr_all_parallel_corpus.txt
	cut -f1 de_fr_all_parallel_lower.txt > de_sent_parallel.txt

$(DIR_OUT)/fr_sent_parallel.txt: $(DIR_OUT)/de_fr_all_parallel_corpus.txt
	cut -f2 de_fr_all_parallel_lower.txt > fr_sent_parallel.txt

all_sent_parallel-target: $(DIR_OUT)/de_sent_parallel.txt $(DIR_OUT)/fr_sent_parallel.txt
