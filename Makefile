# use this

YEARS_START?= 1849
YEARS_END?= 2017
LIMIT_RATE?=32k

PDF_DIR?= data_pdf
TETML_WORD_DIR?=data_tetml-word
TIF_DIR?= data_tif
TIF_COMP_DIR?= data_comp_tif
JPEG_DIR?= data_jpeg2000
DE_SOURCE?=FedGazDe
FR_SOURCE?=FedGazFr
IT_SOURCE?=FedGazIt
JSON_DIR?=canonical_json
IMPORTER_DIR?=impresso-text-acquisition



help:
	# The following steps need to be executed in the given order to get the canonical data that can be ingested into the Impresso platform.
	# To process all languages the source name "FedGazDe" can be replaced with "all".

	# Don't forget to activate the virtual environment with all the requirements installed.
	# Otherwise, the make recipe will fail without proper logging.

	# make download-FedGazDe.bash (get PDF and metadata)

	# make extract-tif-FedGazDe.bash (extract tif from pdf files)
	# make rename-tif-FedGazDe.bash (rename and decompress tif from pdf files)
	# make jp2-FedGazDe-target (convert to canonical jpeg2000)
	# make jp2-ingest-FedGazDe (ingest images into the Impresso platform)

	# make tetml-word-FedGazDe-target (create tetml from pdf files)
	# make data-ingest-FedGazDe (ingest textual data into the Impresso platform)

	# Other functions which are not part of the core pipeline
	# make download-index-all (download index)

run-pipeline-%:
	# TODO
	$(MAKE) -f Makefile extract-tif-$*.bash
	$(MAKE) -f Makefile rename-tif-$*.bash

download-index-all: dl-de dl-it dl-fr dl-1999bar-de dl-1999bar-fr dl-1999bar-it


dl-%:
	for y in $$( seq $(YEARS_START) 1 $(YEARS_END) ) ; do wget -S -N --limit-rate=$(LIMIT_RATE) -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/$${y}/index.html ; done
dl-it:
	for y in $$( seq 1971 1 $(YEARS_END) ) ; do wget -S -N --limit-rate=$(LIMIT_RATE) -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/it/[^f].*"--accept-regex "https://www.admin.ch/opc/it/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/it/federal-gazette/$${y}/index.html ; done

# The issues from 1999 are split into a part from the Bundesarchiv (index_bar.html) and the one from the the "Federal Council"
dl-1999bar-%:
	wget -S -N --limit-rate=14k -A *.html -R *.pdf --regex-type pcre  --reject-regex "https://www.admin.ch/opc/$*/[^f].*"--accept-regex "https://www.admin.ch/opc/$*/federal-gazette/\d+/index.*\.html" -r --no-parent https://www.admin.ch/opc/$*/federal-gazette/1999/index_bar.html

# --accept-regex urlregex
# --regex-type pcre

# Downloading metadata and pdf
article-info-files+= article-info-FedGazDe.tsv
article-info-files+= article-info-FedGazFr.tsv
article-info-files+= article-info-FedGazIt.tsv

article-info-all-target: $(article-info-files)

article-info-FedGaz%.tsv:
	@$(eval LANG_LOWER=$(shell echo $* | tr '[:upper:]' '[:lower:]'))
	python3 lib/gf_html2info.py www.admin.ch/opc/$(LANG_LOWER)/federal-gazette/*/index.html www.admin.ch/opc/$(LANG_LOWER)/federal-gazette/1999/index_bar.html > $@ 2> $@.log || cat $@.log

# document was merged with another one in original source.
# can be removed if document is no longer listed on website.
adhoc-correction-FedGazFr: article-info-FedGazFr.tsv
	sed -i '/10107089/d' $<
download-FedGazFr.bash: adhoc-correction-FedGazFr



download-files += download-FedGazDe.bash
download-files += download-FedGazFr.bash
download-files += download-FedGazIt.bash
download-all-target: $(download-files)

download-%.bash: article-info-%.tsv
	python3 lib/gf_download.py $< > $@ && \
	bash $@


### Extracting Tetml
pdf-FedGazDe-files:=$(wildcard $(PDF_DIR)/$(DE_SOURCE)/*/*/*/*.pdf)
pdf-FedGazFr-files:=$(wildcard $(PDF_DIR)/$(FR_SOURCE)/*/*/*/*.pdf)
pdf-FedGazIt-files:=$(wildcard $(PDF_DIR)/$(IT_SOURCE)/*/*/*/*.pdf)


tetml-word-FedGazDe-files:=$(subst $(PDF_DIR),$(TETML_WORD_DIR),$(pdf-FedGazDe-files:.pdf=.word.tetml))
tetml-word-FedGazFr-files:=$(subst $(PDF_DIR),$(TETML_WORD_DIR),$(pdf-FedGazFr-files:.pdf=.word.tetml))
tetml-word-FedGazIt-files:=$(subst $(PDF_DIR),$(TETML_WORD_DIR),$(pdf-FedGazIt-files:.pdf=.word.tetml))

tetml-word-FedGazDe-target: $(tetml-word-FedGazDe-files)
tetml-word-FedGazFr-target: $(tetml-word-FedGazFr-files)
tetml-word-FedGazIt-target: $(tetml-word-FedGazIt-files)

tetml-word-all-target: tetml-word-FedGazDe-target tetml-word-FedGazFr-target tetml-word-FedGazIt-target

# PDFs before 1999-06-22 need to be treated differently as the last page is not content but metadata
$(TETML_WORD_DIR)/%.word.tetml:$(PDF_DIR)/%.pdf
	mkdir -p $(@D) && \
	if [[ $$(echo $(<D) | sed "s|\(.*\)\(....\)/\(..\)/\(..\)|\2-\3-\4|g") < "1999-06-22" ]] ;\
	then\
		tet -m word --lastpage last-1 --pageopt "tetml={elements={line} glyphdetails={all}} contentanalysis={dehyphenate=true keephyphenglyphs=true}" --outfile $@ -v 3 $< > $@.log ; \
	else \
		tet -m word --pageopt "tetml={elements={line} glyphdetails={all}} contentanalysis={dehyphenate=true keephyphenglyphs=true}" --outfile $@ -v 3 $< > $@.log ; \
	fi


### PDF info files
pdf-info-FedGazFr-files: adhoc-correction-FedGazFr

pdf-info-FedGazDe-files:=$(pdf-FedGazDe-files:.pdf=.pdf.info.txt)
pdf-info-FedGazFr-files:=$(pdf-FedGazFr-files:.pdf=.pdf.info.txt)
pdf-info-FedGazIt-files:=$(pdf-FedGazIt-files:.pdf=.pdf.info.txt)

$(PDF_DIR)/%.pdf.info.txt: $(PDF_DIR)/%.pdf
	pdfinfo $< > $@

pages-all-target: pages-FedGazDe.tsv pages-FedGazFr.tsv pages-FedGazIt.tsv

pages-FedGazDe.tsv: $(pdf-info-FedGazDe-files)
	find $(PDF_DIR)/$(DE_SOURCE) -name '*info.txt' -exec grep -H Pages {} \; | perl -lne 's/\.info\.txt:Pages:\s+/\t/;print;' > $@
pages-FedGazFr.tsv: $(pdf-info-FedGazFr-files)
	find $(PDF_DIR)/$(FR_SOURCE) -name '*info.txt' -exec grep -H Pages {} \; | perl -lne 's/\.info\.txt:Pages:\s+/\t/;print;' > $@
pages-FedGazIt.tsv: $(pdf-info-FedGazIt-files)
	find $(PDF_DIR)/$(IT_SOURCE) -name '*info.txt' -exec grep -H Pages {} \; | perl -lne 's/\.info\.txt:Pages:\s+/\t/;print;' > $@

### Extend current metadata with new information
article-info2-FedGazDe-files:= article-info2-FedGazDe.tsv
article-info2-FedGazFr-files:= article-info2-FedGazFr.tsv
article-info2-FedGazIt-files:= article-info2-FedGazIt.tsv

article-info2-all-target: $(article-info2-FedGazDe-files) $(article-info2-FedGazFr-files) $(article-info2-FedGazIt-files)

article-info2-%.tsv: article-info-%.tsv pages-%.tsv
	python3 lib/extend_metadata.py -i $< -o $@ --dir_pdf $(PDF_DIR) --dir_tif $(TIF_DIR) --pages $(word 2,$^)


### Extract canonical tif files from pdf
extract-tif-FedGazDe-files:= extract-tif-FedGazDe.bash
extract-tif-FedGazFr-files:= extract-tif-FedGazFr.bash
extract-tif-FedGazIt-files:= extract-tif-FedGazIt.bash

extract-tif-all.bash: extract-tif-FedGazDe.bash extract-tif-FedGazFr.bash extract-tif-FedGazIt.bash

# perform for the period with scanned and OCRized documents only
extract-tif-%.bash: article-info2-%.tsv
	python3 lib/pdf2tif.py -i $< --tet $@ --rename $(subst extract,rename,$@) && \
	bash $@ && \
	touch $@


# Decode jbig2 compressed files into tif files
jbig2-FedGazDe-files:=$(wildcard $(TIF_DIR)/$(DE_SOURCE)/*/*/*/*/*.jbig2)
jbig2-FedGazFr-files:=$(wildcard $(TIF_DIR)/$(FR_SOURCE)/*/*/*/*/*.jbig2)
jbig2-FedGazIt-files:=$(wildcard $(TIF_DIR)/$(IT_SOURCE)/*/*/*/*/*.jbig2)


# ensure order as the creation of tif files is not tracked in make
$(jbig2-FedGazDe-files): $(extract-tif-FedGazDe-files)
$(jbig2-FedGazFr-files): $(extract-tif-FedGazFr-files)
$(jbig2-FedGazIt-files): $(extract-tif-FedGazIt-files)


decomp-jbig2-FedGazDe-files:=$(jbig2-FedGazDe-files:.jbig2=.tif)
decomp-jbig2-FedGazFr-files:=$(jbig2-FedGazFr-files:.jbig2=.tif)
decomp-jbig2-FedGazIt-files:=$(jbig2-FedGazIt-files:.jbig2=.tif)

$(TIF_DIR)/%.tif: $(TIF_DIR)/%.jbig2
	jbig2dec $< -o $@

# %-rename-tif.bash gets created implicitly in script pdf2tif.py
rename-tif-FedGazDe-files:= rename-tif-FedGazDe.bash
rename-tif-FedGazFr-files:= rename-tif-FedGazFr.bash
rename-tif-FedGazIt-files:= rename-tif-FedGazIt.bash

# Rename all files after the decompressing of files (which are not tracked within Make)
$(rename-tif-FedGazDe-files): $(decomp-jbig2-FedGazDe-files)
$(rename-tif-FedGazFr-files): $(decomp-jbig2-FedGazFr-files)
$(rename-tif-FedGazIt-files): $(decomp-jbig2-FedGazIt-files)

#tif-rename-FedGazDe: $(rename-tif-FedGazDe-files)
#	bash $@
rename-tif-%.bash: extract-tif-%.bash
	bash $@
	touch $@

# Convert tif into greyscale, 8-bit
tif-FedGazDe-files:=$(wildcard $(TIF_DIR)/$(DE_SOURCE)/*/*/*/*/*.tif)
tif-FedGazFr-files:=$(wildcard $(TIF_DIR)/$(FR_SOURCE)/*/*/*/*/*.tif)
tif-FedGazIt-files:=$(wildcard $(TIF_DIR)/$(IT_SOURCE)/*/*/*/*/*.tif)

gray-tif-FedGazDe-files:=$(subst $(TIF_DIR),$(TIF_COMP_DIR),$(tif-FedGazDe-files:.tif=.gray.tif))
gray-tif-FedGazFr-files:=$(subst $(TIF_DIR),$(TIF_COMP_DIR),$(tif-FedGazFr-files:.tif=.gray.tif))
gray-tif-FedGazIt-files:=$(subst $(TIF_DIR),$(TIF_COMP_DIR),$(tif-FedGazIt-files:.tif=.gray.tif))



$(TIF_COMP_DIR)/%.gray.tif:$(TIF_DIR)/%.tif
	mkdir -p $(@D) && \
	convert -compress lzw $< -depth 8 -colorspace Gray $@


# Convert tif into jpeg2000
jp2-FedGazDe-files:=$(subst $(TIF_COMP_DIR),$(JPEG_DIR),$(gray-tif-FedGazDe-files:.gray.tif=.jp2))
jp2-FedGazFr-files:=$(subst $(TIF_COMP_DIR),$(JPEG_DIR),$(gray-tif-FedGazFr-files:.gray.tif=.jp2))
jp2-FedGazIt-files:=$(subst $(TIF_COMP_DIR),$(JPEG_DIR),$(gray-tif-FedGazIt-files:.gray.tif=.jp2))


jp2-FedGazDe-target: $(jp2-FedGazDe-files)
jp2-FedGazFr-target: $(jp2-FedGazFr-files)
jp2-FedGazIt-target: $(jp2-FedGazIt-files)

jp2-all-target: jp2-FedGazDe-target jp2-FedGazFr-target jp2-FedGazIt-target


$(JPEG_DIR)/%.jp2:$(TIF_COMP_DIR)/%.gray.tif
	mkdir -p $(@D) && \
	opj_compress -r 15 -i $< -o $@



################################################################################
### INGESTION
################################################################################

# Ingest images
jp2-ingest-FedGazDe: $(jp2-FedGazDe-files)
jp2-ingest-FedGazFr: $(jp2-FedGazFr-files)

jp2-ingest-%:
	#s3cmd sync $(JPEG_DIR)/$*/ s3://TRANSFER/$*/jp2/
	rclone sync $(JPEG_DIR)/$*/ s3-impresso:TRANSFER/$*_jp2/ --transfers=8 --verbose --log-file rclone_ingest_jp2_$*.log


jp2-ingestion-all-target: jp2-ingest-FedGazDe jp2-ingest-FedGazFr


# Ingest canonical data, created ad hoc from tetml and metadata file
# NOTE: define the security token SE_ACCESS_KEY and SE_SECRET_KEY as environment variable befoe running the importer

data-ingest-FedGazDe: $(tetml-word-FedGazDe-files)
data-ingest-FedGazFr: $(tetml-word-FedGazFr-files)

data-ingest-%: article-info2-%.tsv
	mkdir dask-space-$*
	cd dask-space-$*

	screen -dmS dask-sched-importer dask-scheduler
	screen -dmS dask-work-importer dask-worker localhost:8786 --nprocs 10 --nthreads 1 --memory-limit 7G

	cd ..

	cp $< $(TETML_WORD_DIR)/$(DE_SOURCE)/metadata.tsv

	python3 impresso-text-acquisition/text_importer/scripts/fedgazimporter.py \
	--input-dir=${CURDIR}/data_tetml-word \
	--clear --output-dir=${CURDIR}/canonical_json \
	--s3-bucket=original-canonical-testing \
	--log-file=log_data-ingest-$*.txt \
	--access-rights=${CURDIR}/access_rights.json \
	--config-file=${CURDIR}/data_ingestion_config_$*.json \
	--scheduler=127.0.0.1:8786 \
	--chunk-size=10

	pkill dask

# NOTE: port forwarding to track progress of ingestion
# ssh -NT USER@SERVERNAME -L8786:localhost:8786


data-ingestion-all-target: data-ingest-FedGazDe data-ingest-FedGazFr


# create random sample images to visually evaluate the calculation of the coordinates (e.g. words, paragraphs)
eval_coordinates-files-all+= eval_coordinates_FedGazDe
eval_coordinates-files-all+= eval_coordinates_FedGazFr
eval_coordinates-files-all+= eval_coordinates_FedGazIt

eval_coordinates_%:
	python3 impresso-text-acquisition/text_importer/importers/tetml/show_canonical_boxes.py -j $(JSON_DIR)/$* --imgdir $(TIF_DIR)/$* --output_suffix .png --output_dir $@ -p 1,0.1,0.1,0.05 --eval batch --page_prob 0.001

# create random sample images of pages with in-page article segmentation
eval_article_segmentation_%:
	python3 impresso-text-acquisition/text_importer/importers/tetml/show_canonical_boxes.py -j $(JSON_DIR)/$* --imgdir $(TIF_DIR)/$* --output_suffix .png --output_dir $@ -p 1,0.1,0.1,0.05 --eval art_segment --page_prob 0.001 --metafile article-info2-$*.tsv

include lib/fg-txt-by-year.mk

SHELL:=/bin/bash
