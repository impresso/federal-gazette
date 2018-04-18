

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


SENTTXT_BY_YEAR?=senttxt-by-year
SENTTXT_PUBLISH_DIR?=/mnt/storage/clfiles/resources/data/corpora/bb-ff-ff/v2016/senttxt

# Collect all texts from a language and compress them locally
collect-senttxt-%:
	mkdir -p senttxt-by-year/$* && for y in data_text/$*/???? ; \
	do \
		find $$y -name "*.cuttered.sent.txt" -exec perl -lne 's/#ST#//;print' "{}" + | \
		gzip -9 > $(abspath $(SENTTXT_BY_YEAR)/$*)/$$(basename $$y).senttxt.gz ; \
	done


de-senttxt-byyear-files:=$(wildcard senttxt-by-year/de/*senttxt.gz)
de-senttxt-byyear-gertwol-files:=$(de-senttxt-byyear-files:.gz=.gertwol.gz)

de-senttxt-byyear-gertwol-target : $(de-senttxt-byyear-gertwol-files)

%.gertwol.gz: %.gz
	zcat $< | tr -s " " "\n" | sort -u | ls-gertwol-utf8 | gertwolscore | gertwol2prolog-utf8.perl -nomorph | gertwol2prolog-utf8  -withpragma SELTEN -txt | gzip -c > $@

senttxt-gertwol-stts-lex.tsv: $(de-senttxt-byyear-gertwol-files)
	zcat $+ | tr -d "\f" |sort -u > $@.tmp
	cut -f 1 $@.tmp | perl -lne 'next unless /-/; print if s/^.+-([^-]{2,})$$/\1/' | sort -u |ls-gertwol-utf8 | gertwolscore | gertwol2prolog-utf8.perl -nomorph | gertwol2prolog-utf8  -withpragma SELTEN -txt > $@.tmp2
	sort -u $@.tmp $@.tmp2 > $@ #&& rm -f $@.tmp $@.tmp2

senttxt-word-freqdist.tsv: $(de-senttxt-byyear-files)
	zcat $+ | tr -s " " "\n" | lib/freqdist.perl > $@
senttxt-gertwol-lex.tsv:
	for y in data_text/de/???? ; \
	do \
		find $$y -name "*.cuttered.sent.txt" -exec perl -lne 's/#ST#//;print' "{}" + | \
		tr -s " " "\n" | sort -u | ls-gertwol-utf8 | gertwolscore | gertwol2prolog-utf8.perl -nomorph | gertwol2prolog-utf8  -withpragma SELTEN -txt ; \
	done | sort -u   > $@



SHELL:=/bin/bash
export SHELLOPTS:=errexit:pipefail
