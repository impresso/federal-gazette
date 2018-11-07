DIR_IN?= data_text
DIR_OUT?= data_alignment

YEARS_START?= 1850
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 20 $(YEARS_END))

de-single-doc-files:=$(patsubst %, $(DIR_OUT)/de_%_all.txt, $(YEARS))
fr-single-doc-files:=$(patsubst %, $(DIR_OUT)/fr_%_all.txt, $(YEARS))
de-translated-doc-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_all.txt, $(YEARS))
de-fr-alignments-doc-files:=$(patsubst %, $(DIR_OUT)/de_fr_%_alignments.xml, $(YEARS))

de-fr-alignments-doc-targets: $(de-single-doc-files) $(fr-single-doc-files) $(de-translated-doc-files) $(de-fr-alignments-doc-files) overview_stats_alignment.csv

# DE: process extracted text data anually and language-wise
de_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_OUT)/,,$*)  FILE_LANG=de DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_OUT)

# FR: process extracted text data anually and language-wise
fr_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$(subst $(DIR_OUT)/,,$*) FILE_LANG=fr DIR_IN=$(DIR_IN) DIR_OUT=$(DIR_OUT)

# Translate all German docs to French with Moses.
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
overview_stats_alignment.csv: de_fr_%_alignments.xml
	head -n 1 *.csv |  sed '2q;d' > csv_header.txt
	awk 'FNR > 1' *.csv > total_stats_alignment.csv
	cat csv_header.txt total_stats_alignment.csv > overview_stats_alignment.csv
	rm csv_header.txt total_stats_alignment.csv
