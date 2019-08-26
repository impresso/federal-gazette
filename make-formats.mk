SHELL:=/bin/bash

# ensure that entire pipe command fails if a part fails
export SHELLOPTS:=errexit:pipefail

DIR_IN?= data_text
DIR_OUT?= data_alignment
FILE_OUT?= $(DIR_OUT)/$(FILE_LANG)_$(YEAR)_all.txt



### SEGMENTATION AND TOKENIZATION WITH cutter
# Make targets for formats derived from the text output
tettext-$(FILE_LANG)-by-year-files:=$(wildcard $(DIR_IN)/$(FILE_LANG)/$(YEAR)/*/*.text)

cuttered-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.txt)
cuttered-$(FILE_LANG)-text-target: $(cuttered-$(FILE_LANG)-text-files)

sent-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.sent.txt)
sent-$(FILE_LANG)-text-target: $(sent-$(FILE_LANG)-text-files)

single-doc-year-file= $(DIR_OUT)/$(FILE_LANG)_$(YEAR)_all.txt
single-doc-year-target: $(single-doc-year-file)


print-%: ; @echo $* is $($*)


# TODO: The output of the cutter doesn't isolate all abbreviations properly.
# Hence, we apply post-processing to merge short tokens (up to 4-gram) and
# the period when followed by a number, a capitalized word oder a lowercased word.
%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter $(FILE_LANG) -T  > $@

# write one tokenized sentence per line
%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@

#write all documents into a single textfile using separator tags
# TODO: Recheck statement as it is probably incorrect (always executed)
#$(FILE_OUT): $(cuttered-$(FILE_LANG)-text-files) $(sent-$(FILE_LANG)-text-files)
%_all.txt: $(sent-$(FILE_LANG)-text-files)
	mkdir -p $(DIR_OUT) && \
	python3 lib/cuttered2single_doc.py -i $(DIR_IN)/$(FILE_LANG)/$(YEAR) -w /**/*cuttered.sent.txt -o $@

### SEGMENTATION AND TOKENIZATION WITH spaCy
# TODO: year-wise processing in order to parallelize. Since all entities

tettext-$(FILE_LANG)-all-files:=$(wildcard $(DIR_IN)/$(FILE_LANG)/*/*/*.text)
sent-$(FILE_LANG)-spacy-text-files:=$(tettext-$(FILE_LANG)-all-files:.text=.spacy.sent.txt)

$(sent-$(FILE_LANG)-spacy-text-files): sent-$(FILE_LANG)-spacy-text-files-batch-process
sent-$(FILE_LANG)-spacy-text-target: $(sent-$(FILE_LANG)-spacy-text-files)

# flag -u to avoid output buffering
# additionally, extract all name entities and count their occurrence
sent-$(FILE_LANG)-spacy-text-files-batch-process: lib/processing_spacy.py
	python3 -u lib/processing_spacy.py -dir $(DIR_IN)/$(FILE_LANG) -l $(FILE_LANG) -f_ne named_entities_$(FILE_LANG).tsv

SHELL:=/bin/bash
