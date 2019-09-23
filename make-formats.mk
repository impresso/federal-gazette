SHELL:=/bin/bash

# ensure that entire pipe command fails if a part fails
export SHELLOPTS:=errexit:pipefail

DIR_IN?= data_text
DIR_OUT?= data_alignment
FILE_OUT?= $(DIR_OUT)/$(FILE_LANG)_$(YEAR)_all.txt

# define source name with an capitalized suffix of the language
SRC_NAME?= FedGaz$(shell FILE_LANG=$(FILE_LANG); echo $${FILE_LANG^})

### SEGMENTATION AND TOKENIZATION WITH cutter
# Make targets for formats derived from the text output
tettext-$(FILE_LANG)-by-year-files:=$(wildcard $(DIR_IN)/$(SRC_NAME)/$(YEAR)/*/*/*.text)

cuttered-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.txt)
cuttered-$(FILE_LANG)-text-target: $(cuttered-$(FILE_LANG)-text-files)

sent-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.sent.txt)
sent-$(FILE_LANG)-text-target: $(sent-$(FILE_LANG)-text-files)

single-doc-year-file= $(DIR_OUT)/$(FILE_LANG)_$(YEAR)_all.txt
single-doc-year-target: $(single-doc-year-file)


print-%: ; @echo $* is $($*)

# self-documenting makefile
help : make-formats.mk
	@sed -n 's/^##//p' $<

## .cuttered.txt	: Tokenized text with one token per line
%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter $(FILE_LANG) -T  > $@

## cuttered.sent.txt	: Tokenized text with one sentence per line and tokens seperated by space
%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@

## _all.txt	: Concat all documents per year using separator tags
# TODO: Recheck statement as it is probably incorrect (always executed)
#$(FILE_OUT): $(cuttered-$(FILE_LANG)-text-files) $(sent-$(FILE_LANG)-text-files)
%_all.txt: $(sent-$(FILE_LANG)-text-files)
	mkdir -p $(@D) && \
	python3 lib/cuttered2single_doc.py -i $(DIR_IN)/$(SRC_NAME)/$(YEAR) -w /**/*cuttered.sent.txt -o $@

### SEGMENTATION AND TOKENIZATION WITH spaCy
# TODO: year-wise processing in order to parallelize.

tettext-$(FILE_LANG)-all-files:=$(wildcard $(DIR_IN)/$(FILE_LANG)/*/*/*.text)
sent-$(FILE_LANG)-spacy-text-files:=$(tettext-$(FILE_LANG)-all-files:.text=.spacy.sent.txt)

$(sent-$(FILE_LANG)-spacy-text-files): sent-$(FILE_LANG)-spacy-text-files-batch-process
sent-$(FILE_LANG)-spacy-text-target: $(sent-$(FILE_LANG)-spacy-text-files)

# flag -u to avoid output buffering
# additionally, extract all name entities and count their occurrence

## .spacy.sent.txt	: Tokenized text with one sentence per line and tokens seperated by space
sent-$(FILE_LANG)-spacy-text-files-batch-process: lib/processing_spacy.py
	python3 -m spacy download $(FILE_LANG)_core_news_md
	python3 -u lib/processing_spacy.py -dir $(DIR_IN)/$(FILE_LANG) -l $(FILE_LANG) -f_ne named_entities_$(FILE_LANG).tsv

SHELL:=/bin/bash
