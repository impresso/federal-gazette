

# use this 

YEARS_START?= 1849
YEARS_END?= 2017
LIMIT_RATE?=32k

DATA_DIR?= data_pdf


help:
	# make download-index
	# make article-info-target

download-index: dl-de dl-it dl-fr dl-1999bar-de dl-1999bar-fr dl-1999bar-it


dl-%:
	for y in $$( seq $(YEARS_START) 1 $(YEARS_END) ) ; do wget -S -N --limit-rate=$(LIMIT_RATE) -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/$${y}/index.html ; done
dl-it:
	for y in $$( seq 1971 1 $(YEARS_END) ) ; do wget -S -N --limit-rate=$(LIMIT_RATE) -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/it/[^f].*"--accept-regex "https://www.admin.ch/opc/it/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/it/federal-gazette/$${y}/index.html ; done

# The issues from 1999 are split into a part from the Bundesarchiv (index_bar.html) and the one from the the "Federal Council"
dl-1999bar-%:
	wget -S -N --limit-rate=14k -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/1999/index_bar.html
	
# --accept-regex urlregex
# --regex-type pcre



article-info-%.tsv:
	python3 lib/gf_html2info.py www.admin.ch/opc/$*/federal-gazette/*/index.html www.admin.ch/opc/$*/federal-gazette/1999/index_bar.html   > $@ 2> $@.log || cat $@.log

todo-download-%.bash: article-info-%.tsv
	python3 lib/gf_download.py $< > $@


article-info-files+= article-info-de.tsv
article-info-files+= article-info-fr.tsv
article-info-files+= article-info-it.tsv

article-info-target: $(article-info-files)

todo-download-files += todo-download-de.bash
todo-download-files += todo-download-fr.bash
todo-download-files += todo-download-it.bash
todo-download-target: $(todo-download-files)



### tet conversion
# word plus with glyphs
DATA_TETML_WORDPLUS_DIR?=data_tetml-wordplus
de-pdf-files:=$(wildcard $(DATA_DIR)/de/*/*/*.pdf)
fr-pdf-files:=$(wildcard $(DATA_DIR)/fr/*/*/*.pdf)
it-pdf-files:=$(wildcard $(DATA_DIR)/it/*/*/*.pdf)

de-textml-wordplus-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORDPLUS_DIR),$(de-pdf-files:.pdf=.wordplus.tetml))
fr-textml-wordplus-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORDPLUS_DIR),$(fr-pdf-files:.pdf=.wordplus.tetml))
it-textml-wordplus-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORDPLUS_DIR),$(it-pdf-files:.pdf=.wordplus.tetml))

de-textml-wordplus-target: $(de-textml-wordplus-files)
fr-textml-wordplus-target: $(fr-textml-wordplus-files) 
it-textml-wordplus-target: $(it-textml-wordplus-files)

all-textml-wordplus-target: de-textml-wordplus-target fr-textml-wordplus-target it-textml-wordplus-target

$(DATA_TETML_WORDPLUS_DIR)/%.wordplus.tetml:$(DATA_DIR)/%.pdf
	mkdir -p $(@D) && \
	tet -m wordplus --outfile $@ -v 3 $< > $@.log

DATA_TETML_WORD_DIR?=data_tetml-word
de-textml-word-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORD_DIR),$(de-pdf-files:.pdf=.word.tetml))
fr-textml-word-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORD_DIR),$(fr-pdf-files:.pdf=.word.tetml))
it-textml-word-files:=$(subst $(DATA_DIR),$(DATA_TETML_WORD_DIR),$(it-pdf-files:.pdf=.word.tetml))

de-textml-word-target: $(de-textml-word-files)
fr-textml-word-target: $(fr-textml-word-files) 
it-textml-word-target: $(it-textml-word-files)

all-textml-word-target: de-textml-word-target fr-textml-word-target it-textml-word-target

$(DATA_TETML_WORD_DIR)/%.word.tetml:$(DATA_DIR)/%.pdf
	mkdir -p $(@D) && \
	tet -m word --outfile $@ -v 3 $< > $@.log

DATA_TEXT_DIR?=data_text
de-text-files:=$(subst $(DATA_DIR),$(DATA_TEXT_DIR),$(de-pdf-files:.pdf=.text))
fr-text-files:=$(subst $(DATA_DIR),$(DATA_TEXT_DIR),$(fr-pdf-files:.pdf=.text))
it-text-files:=$(subst $(DATA_DIR),$(DATA_TEXT_DIR),$(it-pdf-files:.pdf=.text))

de-text-target: $(de-text-files)
fr-text-target: $(fr-text-files) 
it-text-target: $(it-text-files)

all-text-target: de-text-target fr-text-target it-text-target

$(DATA_TEXT_DIR)/%.text:$(DATA_DIR)/%.pdf
	mkdir -p $(@D) && \
	if [[ $$(basename $(<D) ) < "1999-06-22" ]] ;\
	then\
		tet --text --lastpage last-1 --outfile $@ -v 3 $< > $@.log ; \
	else \
		tet --text --outfile $@ -v 3 $< > $@.log ; \
	fi


include lib/fg-txt-by-year.mk

SHELL:=/bin/bash
