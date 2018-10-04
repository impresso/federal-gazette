DATA_DIR?= data_text
FILE_OUT?= $(FILE_LANG)_$(YEAR)_all.txt


# Make targets for formats derived from the text output
tettext-$(FILE_LANG)-by-year-files:=$(wildcard $(DATA_DIR)/$(FILE_LANG)/$(YEAR)/*/*.text)

cuttered-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.txt)
sent-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.sent.txt)

#cuttered-$(FILE_LANG)-text-target: $(cuttered-$(FILE_LANG)-text-files) $(sent-$(FILE_LANG)-text-files)

# $(info $$var is $(FILE_OUT))

# The output of the cutter doesn't isolate all abbreviations properly.
# Hence, we apply post-processing to merge short tokens (up to 4-gram) and
# the period when followed by a number, a capitalized word oder a lowercased word.
%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter $(FILE_LANG) -T  > $@



# write one tokenized sentence per line
%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@

#write all documents into a single textfile using separator tags
$(FILE_OUT): $(cuttered-$(FILE_LANG)-text-files) $(sent-$(FILE_LANG)-text-files)
	python3 lib/cuttered2single_doc.py -i $(DATA_DIR)/$(FILE_LANG)/$(YEAR) -o $@


SHELL:=/bin/bash
