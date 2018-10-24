DIR_IN?= data_text
DIR_OUT?= data_alignment

YEARS_START?= 1850
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 20 $(YEARS_END))

de-single-doc-files:=$(patsubst %, de_%_all.txt, $(YEARS))
fr-single-doc-files:=$(patsubst %, fr_%_all.txt, $(YEARS))
de-translated-doc-files:=$(patsubst %, de_fr_%_all.txt, $(YEARS))
de-fr-alignments-doc-files:=$(patsubst %, de_fr_%_alignments.xml, $(YEARS))

de-alignments-doc-targets: $(de-single-doc-files) $(fr-single-doc-files) $(de-translated-doc-files) $(de-fr-alignments-doc-files)

# DE: process extracted text data anually and language-wise
de_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$* FILE_LANG=de DIR_IN=$(DIR_IN)

# FR: process extracted text data anually and language-wise
fr_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$* FILE_LANG=fr DIR_IN=$(DIR_IN)

# Translate all German docs to French with Moses.
# Remove square brackets as Moses cannot process them
de_fr_%_all.txt: de_%_all.txt
	cat $(DIR_OUT)/$< | \
	/mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/lowercase.perl | \
	sed -r "s/\[//" | sed -r "s/\]//" | \
	moses -f mt_moses/train_de_fr/binarised_model/moses.ini -threads 5 | \
	sed -r "s/^\.eoa/.EOA/" \
	> $(DIR_OUT)/$@

# Compute BLEU-alignments for German and French documents
de_fr_%_alignments.xml: de_%_all.txt fr_%_all.txt de_fr_%_all.txt
	python2 lib/bleualign_articles.py -src $(word 1, $^) -trg $(word 2, $^) \
	-t $(word 3, $^) -o > $(DIR_OUT)/$@
