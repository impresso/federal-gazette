


# Make targets for formats derived from the text text output

tettext-by-year-files:=$(wildcard data_text/de/????/*/*.text)

cuttered-de-text-files:=$(tettext-by-year-files:.text=.cuttered.txt)
sent-de-text-files:=$(tettext-by-year-files:.text=.cuttered.sent.txt)

cuttered-de-text-target: $(cuttered-de-text-files) $(sent-de-text-files)

##$(info ,$(tettext-by-year-files))

%.cuttered.txt: %.text
	perl -lne 's/\d*\s*\f\s*\d*//;print' < $< | cutter de  > $@

%.cuttered.sent.txt: %.cuttered.txt
	python3 lib/cuttered2sent.py $< > $@




SHELL:=/bin/bash
