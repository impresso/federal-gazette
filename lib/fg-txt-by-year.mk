

TXT_BY_YEAR?=txt-by-year
PUBLISH_DIR?=/mnt/storage/clfiles/resources/data/corpora/bb-ff-ff/v2016/txt

# Collect all texts from a language and compress them locally
collect-%:
	mkdir -p txt-by-year/$* && for y in $(DATA_TEXT_DIR)/$*/???? ; \
	do \
		find $$y -name "*.text" -exec perl -lne 's/\f/\n\n\n/;print' "{}" + | \
		gzip -9 > $(abspath $(TXT_BY_YEAR)/$*)/$$(basename $$y).txt.gz ; \
	done


# Move them to an official path
publish-%:
	mkdir -p $(PUBLISH_DIR)/$* && mv $(TXT_BY_YEAR)/$*/*.gz $(PUBLISH_DIR)/$*


collect: collect-de collect-it collect-fr

publish: publish-de publish-it publish-fr


clean:
	rm -rf $(DATA_OUT_DIR_de) $(DATA_OUT_DIR_it) $(DATA_OUT_DIR_fr)

SHELL:=/bin/bash
