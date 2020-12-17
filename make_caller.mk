SHELL:=/bin/bash

# ensure that entire pipe command fails if a part fails
export SHELLOPTS:=errexit:pipefail


PDF_DIR?= data_pdf
TEXT_DIR?= data_text
ALIGN_DIR?= data_align

TRANS_DIR?= /dev/shm/impresso

YEARS_START?= 1849
YEARS_END?= 2017

YEARS:=$(shell seq $(YEARS_START) 1 $(YEARS_END))

# keep all intermediate files
.SECONDARY:

# debug print content of variable
print-%: ; @echo $* is $($*)

################################################################################
### TOKENIZING
################################################################################
# segment and tokenize extracted text data anually and merge into single document

de-single-doc-files:=$(patsubst %, $(ALIGN_DIR)/de_%_all.txt, $(YEARS))
fr-single-doc-files:=$(patsubst %, $(ALIGN_DIR)/fr_%_all.txt, $(YEARS))
it-single-doc-files:=$(patsubst %, $(ALIGN_DIR)/it_%_all.txt, $(YEARS))

de-single-doc-target: $(de-single-doc-files)
fr-single-doc-target: $(fr-single-doc-files)
it-single-doc-target: $(it-single-doc-files)

all-single-doc-target: de-single-doc-target fr-single-doc-target it-single-doc-target

de_%_all.txt:
	@echo 'Segmenting all German documents of the year $(subst $(ALIGN_DIR)/,,$*) and concatenate to a single doc: $@'
	$(MAKE) -f make_segment.mk YEAR=$(subst $(ALIGN_DIR)/,,$*) FILE_LANG=de PDF_DIR=$(PDF_DIR) TEXT_DIR=$(TEXT_DIR) ALIGN_DIR=$(ALIGN_DIR) single-doc-year-target

fr_%_all.txt:
	@echo 'Segmenting all French documents of the year $(subst $(ALIGN_DIR)/,,$*) and concatenate to a single doc: $@'
	$(MAKE) -f make_segment.mk YEAR=$(subst $(ALIGN_DIR)/,,$*) FILE_LANG=fr PDF_DIR=$(PDF_DIR) TEXT_DIR=$(TEXT_DIR) ALIGN_DIR=$(ALIGN_DIR) single-doc-year-target

it_%_all.txt:
	@echo 'Segmenting all Italian documents of the year $(subst $(ALIGN_DIR)/,,$*) and concatenate to a single doc: $@'
	$(MAKE) -f make_segment.mk YEAR=$(subst $(ALIGN_DIR)/,,$*) FILE_LANG=it PDF_DIR=$(PDF_DIR) TEXT_DIR=$(TEXT_DIR) ALIGN_DIR=$(ALIGN_DIR) single-doc-year-target


################################################################################
### DOCUMENT ALIGMNENT
################################################################################


de-fr-trans-doc-files:=$(subst de,de_fr,$(pdf-FedGazDe-files:.txt=_trans.txt))
#de-fr-trans-doc-files:=$(patsubst %, $(ALIGN_DIR)/de_fr_%_trans.txt, $(YEARS))
de-fr-trans-target: $(de-fr-trans-doc-files)

# Translate the German doc into French
de_fr_%_trans.txt: de_%_all.txt
	cat $< | \
	perl /mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/lowercase.perl | \
	perl /mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/escape-special-chars.perl | \
	moses -f mt_moses/train_de_fr/binarised_model/moses.ini -v 0 -threads 1 --minphr-memory --minlexr-memory | \
	perl /mnt/storage/clfiles/resources/applications/mt/moses/vGitHub/scripts/tokenizer/deescape-special-chars.perl | \
	sed -r "s/^\.eoa/.EOA/" | \
	sed -r "s/^\.eob/.EOB/" \
	> $@ \
	|| echo 'Error during Moses translation process for the following year: ' $@ >> log_moses.txt

# Compute BLEU-alignments for German and French documents
de-fr-align-doc-files:=$(patsubst %, $(ALIGN_DIR)/de_fr_%_align.xml, $(YEARS))
de-fr-align-stats-files:=$(de-fr-align-doc-files:.xml=_stats.tsv)
de-fr-align-doc-target: $(de-fr-align-doc-files) $(de-fr-align-stats-files) $(de-fr-trans-doc-files)

de_fr_%_align.xml: de_%_all.txt fr_%_all.txt de_fr_%_trans.txt
	python3 -u lib/bleualign_articles.py -src $(word 1, $^) -trg $(word 2, $^) \
	-t $(word 3, $^) -o $@ -c

de_fr_%_align_stats.tsv: de_fr_%_align.xml
	@echo "The bleualign_articles.py implicitly creates $@ with stats in addition to $<"

# Collect the alignment stats per language pair and merge them into single tsv
de-fr-total-stats-align-target: $(ALIGN_DIR)/total_align_stats_de_fr.tsv $(de-fr-align-stats-files)

$(ALIGN_DIR)/total_align_stats_de_fr.tsv: $(de-fr-align-stats-files)
	head -1 $< > $<.header.temp
	awk 'FNR > 1' $^ > $@.temp
	cat $<.header.temp $@.temp > $@
	rm $<.header.temp $@.temp



################################################################################
### SENTENCE ALIGMNENT
################################################################################

# Firstly, remove first and last line from the translation file (delimiter volume organization)
# Secondly, split this file into its articles at .EOA delimiter and write into RAM.
# Thirdly, rename all article according to its first line
# Fourthly, remove first line in all files which contains the file name

de-fr-translated-dummy:=$(patsubst %, $(ALIGN_DIR)/de_fr_%_trans_dummy.txt, $(YEARS))

de_fr_%_trans_dummy.txt: de_fr_%_trans.txt
	mkdir -p $(TRANS_DIR)/$*
	sed '1d; $$d' $< | csplit -z --digits=4 --quiet --suppress-matched --prefix=$(TRANS_DIR)/$*/trans_art /dev/stdin "/.EOA/" "{*}"
	for i in "$(TRANS_DIR)/$*/"trans_art*; do mv "$$i" "$(TRANS_DIR)/$*/$$(basename $$(cat "$$i"|head -n1))"; done
	sed -i '1d' "$(TRANS_DIR)/$*/"*.cuttered.sent.txt || echo 'Error during pre-processing for the following year: ' $@ >> log_dummy_trans.txt


# Create a tsv-file with all aligned articles (src, trg, translation)
de-fr-aligned-doc-files:=$(patsubst %, $(ALIGN_DIR)/de_fr_%_aligned_docs.tsv, $(YEARS))

de-fr-aligned-doc-target: $(de-fr-aligned-doc-files)

de_fr_%_aligned_docs.tsv: de_fr_%_align.xml de_fr_%_trans_dummy.txt
	python lib/aligned2tsv.py -i $< -o $@ -t $(TRANS_DIR)/$(ALIGN_DIR)


# Align sentences with bleu-champ and set EOA-marker to indicate the article boundaries
# After the alignment, clean up directory with translated files
de-fr-parallel-corpus-files:=$(patsubst %, $(ALIGN_DIR)/de_fr_%_parallel_corpus.tsv, $(YEARS))
de-fr-parallel-corpus-target: $(de-fr-parallel-corpus-files)

de_fr_%_parallel_corpus.tsv: de_fr_%_aligned_docs.tsv
	while IFS=$$'\t' read -r col_src col_trg col_trans ; do bleu-champ -q -s $${col_trans} -t $${col_trg} -S $${col_src} >> $@ ; echo '.EOA '$${col_src}'	.EOA '$${col_trg} >> $@; done < $<
#	rm -r "$(TRANS_DIR)/$*"


# Create a parallel corpus across years as tsv file
$(ALIGN_DIR)/de_fr_all_parallel_corpus.tsv: $(de-fr-parallel-corpus-files)
	cat $^ > $@

# Filter the parallel corpus
$(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.tsv: $(ALIGN_DIR)/de_fr_all_parallel_corpus.tsv
	python3 lib/clean_corpus.py --f_in $< --f_out $@

# Split the parallel corpus into separate files per language
$(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.de: $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.tsv
	cut -f1 $< > $@

$(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.fr: $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.tsv
	cut -f2 $< > $@

de-fr-parallel-corpus-filtered-target: $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.de $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.fr

################################################################################
### PHRASE EXTRACTION
################################################################################
# extract phrases with gensim phrase extraction (scoring with NPMI)
DIR_PHRASES?= phrases
phrases-de-fr-files:= $(DIR_PHRASES)/phrases_bigrams.de $(DIR_PHRASES)/phrases_trigrams.de $(DIR_PHRASES)/phrases_bigrams.fr $(DIR_PHRASES)/phrases_trigrams.fr
phrases-de-fr-target: $(phrases-de-fr-files)
$(DIR_PHRASES)/phrases_bigrams.% $(DIR_PHRASES)/phrases_trigrams.%: $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.%
	mkdir -p $(@D) && \
	python3 lib/phrase_detection.py -l $(*F) -i $< -o phrases --dir $(@D) --trigram

################################################################################
#### MULTILINGUAL EMBEDDINGS
################################################################################

DIR_EMBED?= embedding
DIR_EMBED_DATA?= embedding/data
DIR_EUROPARL?= europarl_data

# Get the official Europarl corpus
$(DIR_EUROPARL)/Europarl.de-fr.de:
	wget http://opus.nlpl.eu/download.php?f=Europarl/v3/moses/de-fr.txt.zip -O $(DIR_EUROPARL).zip; \
	unzip $(DIR_EUROPARL).zip -d $(DIR_EUROPARL); \
	rm $(DIR_EUROPARL).zip

# The French file is created implicitly
 $(DIR_EUROPARL)/Europarl.de-fr.fr: $(DIR_EUROPARL)/Europarl.de-fr.de


europarl-de-fr-cuttered-files:= $(DIR_EUROPARL)/Europarl.de-fr.cuttered.de $(DIR_EUROPARL)/Europarl.de-fr.cuttered.fr
europarl-de-fr-cuttered-target: $(europarl-de-fr-cuttered-files)

# Tokenize Europarl corpus
# cutter produces vertical text.
# Subsequently, make horizontal, remove trailing spaces and add new line with echo
#  -k Keep same order
Europarl.de-fr.cuttered.%: Europarl.de-fr.%
	parallel --progress --pipe -k -N 1 -j 30 "cutter $(*F) -T | tr '\n' ' ' | sed 's/[[:space:]]*$$//' && echo ''" < $< > $@


# Merge with EuroParl corpus
de-fr-parallel-fedgaz-europarl-files:= $(DIR_EMBED_DATA)/de-fr-parallel-fedgaz-europarl.de $(DIR_EMBED_DATA)/de-fr-parallel-fedgaz-europarl.fr
$(DIR_EMBED_DATA)/de-fr-parallel-fedgaz-europarl.%: $(ALIGN_DIR)/de_fr_all_parallel_corpus_filtered.% $(DIR_EUROPARL)/Europarl.de-fr.cuttered.%
	mkdir -p $(@D) && \
	cat $^ > $@

# Prepare data (French is cleaned implicitly)
de-fr-sent-parallel-clean-de-files:=$(DIR_EMBED_DATA)/de_fr_parallel_clean.de
de-fr-sent-parallel-clean-fr-files:=$(DIR_EMBED_DATA)/de_fr_parallel_clean.fr
de-fr-sent-parallel-clean-files:= $(de-fr-sent-parallel-clean-de-files) $(de-fr-sent-parallel-clean-fr-files)

$(de-fr-sent-parallel-clean-de-files): $(de-fr-parallel-fedgaz-europarl-files)
	python2 lib/multivec_scripts/prepare-data.py $(<:.de=) $(@:.de=) de fr \
	--lowercase --normalize-digits --min-count 5 --shuffle --script lib/multivec_scripts --threads 30 --verbose
$(de-fr-sent-parallel-clean-fr-files): $(de-fr-sent-parallel-clean-de-files)

# keep only alpha-numeric characters, underscore, and hyphen
de-fr-sent-parallel-clean-nopunc-files:= $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.de $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.fr

# remove all special characters if preceded by a initial space (i.e. non-alphanumeric token)
# this is foremost a clean up for OCR errors
de_fr_parallel_clean_nopunc.%: de_fr_parallel_clean.%
	cat $< | sed "s/ [^[:alnum:] <_-]\+/ /g" | sed "s/ \+/ /g" | sed '/.EOA/d' > $@

de-fr-prepare-embedding-data-target: $(de-fr-sent-parallel-clean-nopunc-files) $(de-fr-parallel-fedgaz-europarl-files)


# Train multivec models with 100 dimensions
vectors-100-de-fr-target: $(DIR_EMBED)/vectors.100.de-fr.de.vec $(DIR_EMBED)/vectors.100.de-fr.fr.vec

$(DIR_EMBED)/biskip.100.de-fr.bin: $(de-fr-sent-parallel-clean-nopunc-files)
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 100 --min-count 10 --window-size 10 --threads 30 --iter 20 --sg --save $@

$(DIR_EMBED)/biskip.100.de-fr.de.bin: $(DIR_EMBED)/biskip.100.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.100.de-fr.fr.bin: $(DIR_EMBED)/biskip.100.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.100.de-fr.de.vec: $(DIR_EMBED)/biskip.100.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.100.de-fr.fr.vec: $(DIR_EMBED)/biskip.100.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@



# Train multivec models with 150 dimensions
vectors-150-de-fr-target: $(DIR_EMBED)/vectors.150.de-fr.de.vec $(DIR_EMBED)/vectors.150.de-fr.fr.vec

$(DIR_EMBED)/biskip.150.de-fr.bin: $(de-fr-sent-parallel-clean-nopunc-files)
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 150 --min-count 10 --window-size 10 --threads 30 --iter 20 --sg --save $@

$(DIR_EMBED)/biskip.150.de-fr.de.bin: $(DIR_EMBED)/biskip.150.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.150.de-fr.fr.bin: $(DIR_EMBED)/biskip.150.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.150.de-fr.de.vec: $(DIR_EMBED)/biskip.150.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.150.de-fr.fr.vec: $(DIR_EMBED)/biskip.150.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@

# Train multivec models with 300 dimensions
vectors-300-de-fr-target: $(DIR_EMBED)/vectors.300.de-fr.de.vec $(DIR_EMBED)/vectors.300.de-fr.fr.vec

$(DIR_EMBED)/biskip.300.de-fr.bin: $(de-fr-sent-parallel-clean-nopunc-files)
	mkdir -p $(@D) && \
	multivec-bi --train-src $(word 1, $^) --train-trg $(word 2, $^) --dimension 300 --min-count 10 --window-size 10 --threads 30 --iter 20 --sg --save $@

$(DIR_EMBED)/biskip.300.de-fr.de.bin: $(DIR_EMBED)/biskip.300.de-fr.bin
	multivec-bi --load $< --save-src $@

$(DIR_EMBED)/biskip.300.de-fr.fr.bin: $(DIR_EMBED)/biskip.300.de-fr.bin
	multivec-bi --load $< --save-trg $@

$(DIR_EMBED)/vectors.300.de-fr.de.vec: $(DIR_EMBED)/biskip.300.de-fr.de.bin
	multivec-mono --load $< --save-vectors $@

$(DIR_EMBED)/vectors.300.de-fr.fr.vec: $(DIR_EMBED)/biskip.300.de-fr.fr.bin
	multivec-mono --load $< --save-vectors $@

vectors-all-de-fr-target: vectors-100-de-fr-target vectors-150-de-fr-target vectors-300-de-fr-target

%.mkdir-eval-emb:
	mkdir -p $(@D)

# Evaluate embeddings with MUSE framework
# the script needs to be run within MUSE as pathes to resources are hard-coded
$(DIR_EMBED)/eval/FedGaz-%-eval-outdomain/train.log: $(DIR_EMBED)/vectors.%.de-fr.de.vec $(DIR_EMBED)/vectors.%.de-fr.fr.vec
	cd MUSE && python evaluate.py --src_lang de --tgt_lang fr --src_emb ../$(word 1, $^) --tgt_emb ../$(word 2, $^) --emb_dim $* --max_vocab -1 --cuda False --exp_path ../$(DIR_EMBED) --exp_id FedGaz-$*-eval-outdomain --exp_name eval
	cd ..

$(DIR_EMBED)/eval/FedGaz-%-eval-indomain/train.log: $(DIR_EMBED)/vectors.%.de-fr.de.vec $(DIR_EMBED)/vectors.%.de-fr.fr.vec de-fr-in-domain-dico.txt
	cd MUSE && python evaluate.py --src_lang de --tgt_lang fr --src_emb ../$(word 1, $^) --tgt_emb ../$(word 2, $^) --emb_dim $* --max_vocab -1 --cuda False --exp_path ../$(DIR_EMBED) --exp_id FedGaz-$*-eval-indomain --exp_name eval --dico_eval ../$(word 3, $^)
	cd ..

DIMENSION=100 150 300
muse-eval-indomain-files:=$(patsubst %, $(DIR_EMBED)/eval/FedGaz-%-eval-indomain/train.log, $(DIMENSION))
muse-eval-outdomain-files:=$(patsubst %, $(DIR_EMBED)/eval/FedGaz-%-eval-outdomain/train.log, $(DIMENSION))
eval-emb-dirs:=$(muse-eval-indomain-files:train.log=.mkdir-eval-emb) $(muse-eval-outdomain-files:train.log=.mkdir-eval-emb)
eval-emb-dirs-target: $(eval-emb-dirs)

muse-eval-embeddings-target:  $(muse-eval-indomain-files) $(muse-eval-outdomain-files)


###############################################################
### CLEAN UP
###############################################################
clean:
	rm -r data_alignment
	rm *.bash *.txt *.log
	rm -r /dev/shm/impresso


###############################################################
### UNUSED PARTS
###############################################################

### train, align, and evaluate FastText embeddings
fastText-install:
	git clone https://github.com/facebookresearch/fastText.git
	$(MAKE) -f fastText/make

DIR_FASTTEXT?= fasttext_embedding
fasttext-300-de-fr-files:= $(DIR_FASTTEXT)/fasttext.300.de.vec $(DIR_FASTTEXT)/fasttext.300.fr.vec
fasttext-100-de-fr-files:= $(DIR_FASTTEXT)/fasttext.100.de.vec $(DIR_FASTTEXT)/fasttext.100.fr.vec
fasttext-300-de-fr-target: $(fasttext-300-de-fr-files)
fasttext-de-fr-target: $(fasttext-100-de-fr-files) $(fasttext-300-de-fr-files)

# Train monolingual fastText embeddings with dimension 100
$(DIR_FASTTEXT)/fasttext.100.%.vec: $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.%
	mkdir -p $(@D) && \
	fastText/fasttext skipgram -input $< -output $(@:.vec=) -thread 30 -minCount 5 -ws 10 -dim 100 -epoch 10

# Train monolingual fastText embeddings with dimension 300
$(DIR_FASTTEXT)/fasttext.300.%.vec: $(DIR_EMBED_DATA)/de_fr_parallel_clean_nopunc.%
	mkdir -p $(@D) && \
	fastText/fasttext skipgram -input $< -output $(@:.vec=) -thread 30 -minCount 5 -ws 10 -dim 300 -minn 3 -maxn 6 -epoch 50

DIR_MUSE?= $(DIR_FASTTEXT)/muse
muse-300-de-fr-files:= $(DIR_MUSE)/vectors-de.txt $(DIR_MUSE)/vectors-fr.txt
muse-300-de-fr-target: $(muse-300-de-fr-files) MUSE

$(DIR_MUSE)/vectors-de.txt: $(fasttext-300-de-fr-files)
	cd MUSE && python3 supervised.py --src_lang de --tgt_lang fr --src_emb  ../$(word 1, $^) --tgt_emb  ../$(word 2, $^) --n_refinement 5 --dico_train default --cuda false --exp_path ../$(@D) --exp_name FedGaz --exp_id 0000

$(DIR_MUSE)/vectors-fr.txt: $(fasttext-300-de-fr-files)
