

# use this 

YEARS_START?= 1849
YEARS_END?= 2017
LIMIT_RATE?=32k

DATA_DIR?= data

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

todo-download-%.sh: article-info-%.tsv
	python3 lib/gf_download.py $< > $@


article-info-files+= article-info-de.tsv
article-info-files+= article-info-fr.tsv
article-info-files+= article-info-it.tsv

article-info-target: $(article-info-files)

todo-download-files += todo-download-de.sh
todo-download-files += todo-download-fr.sh
todo-download-files += todo-download-it.sh
todo-download-target: $(todo-download-files)


SHELL:=/bin/bash
