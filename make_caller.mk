DIR_IN?= data_text
DIR_OUT?= data_alignment

YEARS_START?= 1850
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 100 $(YEARS_END))



de-single-doc-files:=$(patsubst %, de_%_all.txt, $(YEARS))
de-translated-doc-files:=$(patsubst %, de_fr_%_all.txt, $(YEARS))

de-translated-doc-targets: $(de-translated-doc-files) $(de-single-doc-files)

# DE: process extracted text data anually and language-wise
de_%_all.txt:
	$(MAKE) -f make-formats.mk YEAR=$* FILE_LANG=de DIR_IN=$(DIR_IN)

de_fr_%_all.txt: de_%_all.txt
	cat $(DIR_IN)/$< | \
	/mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/lowercase.perl | \
	sed -r "s/\[//" | sed -r "s/\]//" | \ # remove square brackets as Moses cannot process them
	moses -f mt_moses/train_de_fr/binarised_model/moses.ini -threads 2 | \
	sed -r "s/^\.eoa/.EOA/" \
	> $(DIR_IN)/$@
