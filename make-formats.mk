DATA_DIR?= data_text



# Make targets for formats derived from the text output
tettext-$(FILE_LANG)-by-year-files:=$(wildcard $(DATA_DIR)/$(FILE_LANG)/$(YEAR)/*/*.text)

cuttered-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.txt)
sent-$(FILE_LANG)-text-files:=$(tettext-$(FILE_LANG)-by-year-files:.text=.cuttered.sent.txt)

cuttered-$(FILE_LANG)-text-target: $(cuttered-$(FILE_LANG)-text-files) $(sent-$(FILE_LANG)-text-files)

#$(info $$var is $(DATA_DIR))
#$(info $$var is $(tettext-$(FILE_LANG)-by-year-files))
#$(info $$var is $(cuttered-$(FILE_LANG)-text-files))

%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter $(FILE_LANG) > $@

%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@




SHELL:=/bin/bash
