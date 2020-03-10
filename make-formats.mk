SHELL:=/bin/bash

# ensure that entire pipe command fails if a part fails
export SHELLOPTS:=errexit:pipefail

ALIGN_DIR?= data_alignment
PDF_DIR?= data_pdf
TEXT_DIR?= data_text


# define source name with an capitalized suffix of the language
SRC_NAME?= FedGaz$(shell FILE_LANG=$(FILE_LANG); echo $${FILE_LANG^})


print-%: ; @echo $* is $($*)

# self-documenting makefile
help: make-formats.mk
	@sed -n 's/^##//p' $<

### EXTRACTING TEXT FROM PDFs WITH tet
pdf-files:=$(wildcard $(PDF_DIR)/$(SRC_NAME)/$(YEAR)/*/*/*.pdf)
text-files:=$(subst $(PDF_DIR),$(TEXT_DIR),$(pdf-files:.pdf=.text))
text-target: $(text-files)


$(TEXT_DIR)/%.text:$(PDF_DIR)/%.pdf
	mkdir -p $(@D) && \
	if [[ $$(basename $(<D) ) < "1999-06-22" ]] ;\
	then\
		tet --text --lastpage last-1 --outfile $@ -v 3 $< > $@.log ; \
	else \
		tet --text --outfile $@ -v 3 $< > $@.log ; \
	fi



### SEGMENTATION AND TOKENIZATION WITH cutter
# Make targets for formats derived from the text output
cuttered-text-files:=$(text-files:.text=.cuttered.txt)
cuttered-text-target: $(cuttered-text-files)

sent-text-files:=$(text-files:.text=.cuttered.sent.txt)
sent-text-target: $(sent-text-files)



### TOKENIZATION and SENTENCE SEGMENTATION WITH cutter
## .cuttered.txt	: Tokenized text with one token per line
# filtering printed page numbers with perl
%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter $(FILE_LANG) -T  > $@

## cuttered.sent.txt	: Tokenized text with one sentence per line and tokens seperated by space
%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@

## _all.txt	: Concat all documents per year using separator tags
# TODO: Recheck statement as it is probably incorrect (always executed)
single-doc-year-file= $(ALIGN_DIR)/$(FILE_LANG)_$(YEAR)_all.txt
single-doc-year-target: $(single-doc-year-file)

%_all.txt: $(sent-text-files)
	mkdir -p $(@D) && \
	python3 lib/cuttered2single_doc.py -i $(TEXT_DIR)/$(SRC_NAME)/$(YEAR) -w /**/*cuttered.sent.txt -o $@


### SEGMENTATION AND TOKENIZATION WITH spaCy
# TODO: year-wise processing in order to parallelize.

pdf-all-year-files:=$(wildcard $(PDF_DIR)/$(SRC_NAME)/$(YEAR)/*/*/*.pdf)
text-all-year-files:=$(subst $(PDF_DIR),$(TEXT_DIR),$(pdf-all-year-files:.pdf=.text))

sent-spacy-text-files:=$(text-all-year-files:.text=.spacy.sent.txt)

$(sent-spacy-text-files): sent-spacy-$(SRC_NAME)-text-files-batch-process
sent-%-spacy-text-target: $(sent-spacy-text-files)

# flag -u to avoid output buffering
# additionally, extract all name entities and count their occurrence

## .spacy.sent.txt	: Tokenized text with one sentence per line and tokens seperated by space
sent-%-spacy-text-files-batch-process: lib/processing_spacy.py
	python3 -m spacy download $*_core_news_md
	python3 -u lib/processing_spacy.py -dir $(TEXT_DIR)/$* -l $* -f_ne named_entities_$*.tsv

SHELL:=/bin/bash
