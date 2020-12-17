# Federal Gazette Corpus 

The [Federal Gazette](https://www.admin.ch/gov/de/start/bundesrecht/bundesblatt/erlaeuterungen-zum-bundesblatt.html) is a journal published by the Swiss Government. The journal is a political newsletter concerned with resolutions and laws of the Swiss Confederation. First published in 1849, briefly after the foundation of the Swiss Federal State, it is provided in the following official languages:

- German ("Bundesblatt") 
- French ("Feuille fédérale")
- Italian ("Foglio federale")

Our pipeline covers the period between 1849 and 2017 for French and German. Although the Italian data is downloaded, it is not further processed. Moreover, the Italian Federal Gazette is only available starting from 1971.

## General structure of the Federal Gazette publications
 - The Federal Gazette has one or more volumes (German "Band") per year (numbered from `I` by roman numbers). Before 1998, each volume started with page number `1`.
 - Each volume consists of several issues (German "Heft") (numbered from `1` by Arabic numbers within each volume). 
 - Each issue consists of several articles. In earlier editions, more than one article can appear on a single page. 

The schema for page numbering in volumes changes starting with the year 1998. Before 1 January 1998, the page numbering of each volume starts from `1`. Moreover, the earlier period may contain in-page article segmentations meaning that a new article begins on the same page where the previous article ends. In these cases, the page comprising the boundary is redundantly assigned to the PDFs of both articles. For the sake of consistency, such pages need additional processing to define the correct article boundary.

The index of keywords is published separately for each volume. Moreover, each text reference includes the volume number and page number (e.g., [this article](https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10046396))

After 1 January 1998, the pages of a whole year are numbered consecutively, and the index of keywords directly references the (unique) page numbers of a volume (e.g., [this article](https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10054877)).

Starting from 22 June 1999, there is no volume organization anymore.

Sometimes the official document does not contain anything due to some data privacy (e.g., [this article](https://www.admin.ch/opc/de/federal-gazette/2016/1506.pdf) or [this)](https://www.admin.ch/opc/de/federal-gazette/2015/1376.pdf).

## Installation and preparatory steps

### Quick setup


```bash
# clone the repository
git clone https://github.com/impresso/federal-gazette

cd federal-gazette

# set up the virtual Python environment
pipenv --python 3.6

# install the dependencies
pipenv install -r requirements.txt --skip-lock
```

We use a number of non-Python dependencies that need to be installed manually.

### pipenv

This repository is tested for Python 3.6 only. Use the pipenv command from above to set up a virtual environment for this particular Python version and install the necessary packages. 

`pipenv` goes beyond the capabilities of the combination of `pip` and `venv` replicates an identical working environment using the `requirements.txt` or`Pipfile`. 

### rclone

`rclone` is used to transfer data between the local host and s3. Set up as follows:

* install with `curl ``https://rclone.org/install.sh`` | sudo bash`
* copy the following configuration in  `~/.config/rclone/rclone.conf` and replace email, access and secret keys.

```
[s3-impresso]
type = s3
env_auth = false
# first.last@epfl.ch @ impresso ZH
access_key_id = ***
secret_access_key = ***
endpoint = https://os.zhdk.cloud.switch.ch
acl = private
region =
storage_class =
```

Then, you can access remote buckets via `remote:path`, e.g.:

```bash
rclone ls s3-impresso:original-canonical-testing/FedGazFr
```

### Other non-Python dependencies

- convert: https://imagemagick.org/index.php
- opj_compress: http://manpages.ubuntu.com/manpages/cosmic/man1/opj_compress.1.html
- pdfinfo: https://www.xpdfreader.com/pdfinfo-man.html
- Install [Tet](https://www.pdflib.com/products/tet/overview/) to extract content from PDFs
- Install [Moses](http://www.statmt.org/moses/index.php?n=Main.omePage) for translating documents in order to align them crosslingually
- Install  [cutter](https://pub.cl.uzh.ch/wiki/public/cutter/start#source) for tokenizing documents
  - make executable as a script
  - used v2.4
- Install [bleu-champ](https://github.com/emjotde/bleu-champ) to sentence align two documents.

```bash
mkdir build
cd build
cmake ..
make
```

- Install the [multiVec toolkit](https://github.com/eske/multivec.git) to train cross-lingual embeddings

```bash
git clone https://github.com/eske/multivec.git
mkdir multivec/build
cd multivec/build
cmake ..
make
cd ..
```

- Install [MUSE framework](https://github.com/facebookresearch/MUSE.git) for aligning and evaluation cross-lingual embeddings

```bash
git clone https://github.com/facebookresearch/MUSE.git
cd MUSE/data
./get_evaluation.sh
```



## Documentation of Processing Pipeline

This documentation describes the processing steps of the raw data for the Federal Gazette into the canonical format required to create the canonical format used in the *Impresso* project. The processing pipeline builds on GNU `make`. 

### Processing Pipeline

The download and build process of the corpus is defined via `make` targets in the file `Makefile`. The scraping and processing of the data is performed separately for each language. We use abbreviated journal names per language:

- FedGazDe (German)
- FedGazFr (French)
- FedGazIt (Italian)

The resulting data for each processing step has the following structure: `data_XX/{JOURNAL_NAME}/{YYYY}/{MM}/{DD}/{EDITION}`.

#### Steps of Pipeline

Unfortunately, `make` needs to be called multiple times as not all the files can be tracked over the entire process due to unknown outputs from some of the invoked python scripts.

To recursively run the entire pipeline for a single language, use the following command:

```bash
make run-pipeline-%
```
The wildcard symbol `%` has to be replaced with the canonical name of the resource (`FedGazDe`, `FedGazFr` `FedGazIt`). In the case of the German `FedGazDe`, for example, the recipe above recursively runs the following recipes:

```bash
# download the entire index for all languages
make download-index-all

# scrape PDF and metadata
make download-FedGazDe.bash 

# create tetml from pdf files
make tetml-word-FedGazDe-target
# produce canonical data and ingest on s3
make data-ingest-FedGazDe

# extract tif from pdf files
make extract-tif-FedGazDe.bash
# rename and decompress tif from pdf files
make rename-tif-FedGazDe.bash
# convert to canonical jpeg2000
make jp2-FedGazDe-target
```



There are more recipes, however, the dependencies are correctly set for the others. Thus, there is no need to call them separately.

### Downloading the HTML index files with all metadata for a given language and period

We use `wget` to download the `html` files with relevant information into a folder structure under `www.admin.ch`.

The download is throttled by default to `32k`. This results in decent behavior without blocking. Additionally, the wget call makes sure that files that are already locally available and for which no newer version is available are not downloaded again.

The make target `download-index-all` downloads all necessary files for all languages. 

Example call for specific download of the French Federal Gazette issues from 1849 to 2017:

```bash
YEARS_START=1849 YEARS_END=2017 make dl-fr
```

#### Complications

The year 1999 is split between material from the Bundesarchiv and the Federal Council. Therefore, there are two index files from 1999. `indexbar.html` from the Bundesarchiv and `index.html` from the Federal Council.

### Extracting the metadata from the index files
All information about each article is stored in a tab-separated text file (e.g., `article-info-FedGazDe.tsv` for all German articles).


The script `lib/gf_html2info.py` compiles this information from the HTML index files. The make target `article-info-all-target` compiles all three languages.

```bash
make article-info-all-target
```

### Downloading the PDF files

1. Each file from the Bundesarchiv has a unique numeric article ID `NNNNNNNNN`. 
2. Each file from the Federal Council gets an unofficial unique article ID by concatenating the year and the first page: `YYYY_PAGE`.

This results in a unique identifier as each article starts on a separate page in the period starting from 1999. The article identifier is used as file name, while the data is organized by newspaper and date as follows:

`data_pdf/{JOURNAL_NAME}/{YYYY}/{MM}/{DD}/{ARTICLEID}.pdf `

The download process is a two-step process:
 1. The script `lib/gf_download.py` reads the metadata file (e.g., `article-info-FedGazDe.tsv`) and checks whether the PDF per article has been downloaded already. If not, then the corresponding shell commands are emitted. The make target `download-all-target` creates the shell files for all three languages (e.g., `download-FedGazDe.bash`).
 2. After assembling the file with the shell commands (e.g., `download-FedGazDe-target.bash`), the same make recipe runs the script, and the downloaded PDFs are saved to `data_pdf`.

A download limit rate of `500kb` seems reasonable for throttling the process.

The meta-data file per language and the article PDFs are the only data used by the canonization procedure described in the following section.

### Conversion from PDF to TETML

The PDFs contain text that is rendered as invisible elements originating from an OCR procedure. We use the [TET library](https://www.pdflib.com/products/tet/) to extract the textual content resulting in TETML files. In the case of German, the extraction is performed with the following recipe:

```bash
make tetml-word-FedGazDe-target
```

The extraction of TETML works on the level of words while preserving all details about individual glyphs to subsequently compute the coordinates of the bounding boxes surrounding words and paragraphs, respectively. Moreover, the hyphenation of words is kept and reconstructed at a later stage. The TET extraction routine ignores pages containing metadata only by defining the page range. 

The extracted TETML files are written to `data_tetml-word`. Moreover, these files are the source to be further processed by the tetml-importer provided as part of our [Impresso-text-acquisition](https://impresso.github.io/impresso-text-acquisition/) package, as described below.

### Conversion from PDF to JPEG2000

Due to limited conversion functionalities, the canonical images have to be transformed over several steps. Firstly, we use the [TET library](https://www.pdflib.com/products/tet/) to extract TIF images from all the PDFs. Similar to the textual data transformation process, the images are only extracted up to their last full page to avoid redundant images because of in-page article boundaries. For this reason, the extraction builds on an extended metadata file described in the [section about article segmentation](#anchors-logical-article-segmentation).

```bash
make extract-tif-FedGazDe.bash 
```

After the extraction, the individual pages need to be renamed accordingly. As some of the TIF files are compressed, `jbig2dec` is used to decode the images before any further processing. The decompressing and renaming is performed with the following recipe:

```bash
make rename-tif-FedGazDe.bash
```

The black/white images are then converted into 8bit grayscale TIF using ImageMagick. This intermediate step is necessary due to input restrictions of OpenJPEG. We use OpenJPEG to convert the TIF to JPEG2000 and compress them with a ratio of `15` with the following recipe:

```bash
make jp2-FedGazDe-target
```

The files are written to `data_jpeg2000` and used for the publication on the Impresso platform.

### Canonization and ingestion of data 

The [Impresso-text-acquisition](https://impresso.github.io/impresso-text-acquisition/) package provides several importers, among them the `tetml-importer` `fedgaz-importer`. These importers parse the TETML files on a per issue basis and transforms them into the [canonical JSON format](https://github.com/impresso/impresso-schemas) required by the Impresso platform. An issue consists of articles published on the same day.

Specifically, the importer yields a single JSON file per year, comprising an overview of all published issues, along with a JSON for each page, which contains the actual content. The coordinates are computed relative to the size of the TIF image (actual scan) whereby a specific text element gets the coordinates by drawing a new bounding box around all lower-level elements (region > paragraphs > lines > words).

To perform a logical article segmentation, the `fedgaz-importer` has to be used instead of the generic `tetml-importer`. This custom importer inherits most of its class methods from the generic importer, however, it accounts for the specificities of the FedGaz data. Specifically, it features a heuristic search of the title on the first page of the subsequent article to set exact article boundaries ([see article segmentation](#anchors-logical-article-segmentation)). The remainder on this page belonging to the previous article is then moved into a separate region and assigned to the correct article. This importer may be well used for other resources that need a post hoc logical article segmentation.

#### Ingest Text Data

The importer performs the canonization of the textual data and its upload to s3 in a single step. We can start the import process by calling the following recipe:

```bash
make data-ingest-FedGazDe
```

To upload the data to s3, the following environment variable needs to be set:

```bash
export SE_ACCESS_KEY=X
export SE_SECRET_KEY=X
```

#### Ingest Image Data

The upload of the canonical images is separated from the textual data and may be started with the following recipe:

```bash
make jp2-ingest-FedGazDe
```

We use `rclone` instead of `s3cmd` as it allows parallel transfers and is also more robust when processing big chunks of data. 

### Logical Article Segmentation

The heuristic search of the `fedgaz-importer` requires additional metadata to set the correct article boundaries. As a first step, potential pages that belong to two articles need to be identified. While theoretically easy, it is challenging in practice as the page numbers reported in the metadata maybe not in line with the physical page numbering printed on the respective pages. For example, some articles belonging to the appendix (Beilagen) may have a reported length of one page and, according to the official metadata, would overlap with other articles at the end of the issue. However, this information is not reliable. 

To account for such erroneous  information, `pdfinfo` collects the actual length of articles. Based on the original metadata and the physical length, a messy script `lib/extend_metadata.py` determines the actual pages of an article and indicates a potential overlap following heuristics. The extended metadata file (e.g., `article-info2-FedGazDe.tsv`) is subsequently used in the process of the logical article segmentation.

The `fedgaz-importer` requires the extended metadata file named `metadata.tsv`  in the top-level directory of the TETML folder (e.g., `data_tetml-word/FedGazDe/metadata.tsv`). The importer uses this resource to look up additional information and narrow down on article candidates with potential in-page boundaries. Specifically, the metadata needs to include the following columns: `article_docid` (used as lookup key), `article_title`, `volume_language`, `pruned`, `canonical_page_first`, and `canonical_page_last` (indicating the last page of an article covering a full page and, thus, excluding a potential remainder before an in-page boundary). 

This non-generic importer implements a logical article segmentation to determine the actual boundary and reassign the content to the respective article. 

For detecting the correct article boundary, a fuzzy match procedure tries to find the subsequent article's title within its first page. The fuzziness is defined as a function of the title length, which is additionally pruned to a maximum length. Thus, the approach works only reasonable for well-restored OCR-texts. A too relaxed threshold would lead to many false-positives. In cases where the boundary cannot be found, the remainder of an article keeps to be a part of the subsequent article ensuring non-redundant content.

#### Evaluation of Article segmentation

Although included as recipes in the same Makefile, the following evaluation steps are not part of the core pipeline. Both recipes are aimed to manually evaluate the visual alignments between the coordinates of textual elements in canonical JSON files and the canonical images. 

```bash
make eval_coordinates_FedGazDe
```

The evaluation runs the Python script `impresso-text-acquisition/text_importer/importers/tetml/show_canonical_boxes.py`. The script generates a random sample of page images with bounding boxes surrounding an equally random selection of tokens, lines, and article regions. 

Similarly, the following evaluation aims to check the heuristic article segmentation. Thus, it samples only pages comprising an in-page segmentation. Supposedly, a new article begins on the same page where the previous article ends.

```bash
make eval_article_segmentation_FedGazDe
```



## Documentation on Parallel Corpus of Federal Gazette and Bilingual Embeddings

This report describes the construction of the parallel corpus of the Federal Gazette Archive and the bilingual embeddings DE-FR, trained on this corpus. The parallel corpus is sentence as well as document-aligned using separators.

The pipeline requires the article PDF to be present as described in the [download section](#anchors-downloading-pdf-files). As before, the collection and processing of data follow an organization per language (DE, FR, IT).

There are two `Makefiles` to keep the process as simple as possible, while avoiding redundancies of commands between the languages:

- `make_caller.mk` (main pipeline to train bilingual embeddings)
- `make_segment.mk` (segment articles per language)

You only need to call the `make_caller.mk` , while the `make_segment.mk ` gets recursively called in the background. As all the dependencies are correctly set, you can simply call the final recipe to run the entire pipeline.

```bash
make -f make_caller.mk muse-eval-embeddings-target
```

Moreover, the processing pipeline can be easily parallelized when using make. Set the parameter `-j` according to the number of parallel processes. You need to choose the number of parallel tasks carefully and within the limits of your system to avoid errors due to memory limits (e.g., the translation with Moses is computationally expensive). Additionally, `nohup` may be used to start the task as background process and log the console to a file:
```bash
nohup make -f make_caller.mk muse-eval-embeddings-target -j 20 > log_parallel_corpus_embeddings.txt
```

Without further specification, all documents will be processed. However, the start and the end of the period that needs to be processed can be manually controlled with additional variables in the Makefile:

-  `YEARS_START=1965` 
-  `YEARS_END=2000` 

### Extraction and segmentation of texts

The pipeline starts with the extraction of the OCRized plain text of the PDFs using TET. The extraction and the subsequent segmentation is performed in a second Makefile to avoid redundant recipes. This other Makefile is called per language and year year-wise:

```bash
# e.g., FedGazDe
$(MAKE) -f make_segment.mk YEAR=$(subst $(ALIGN_DIR)/,,$*) FILE_LANG=de PDF_DIR=$(PDF_DIR) TEXT_DIR=$(TEXT_DIR) ALIGN_DIR=$(ALIGN_DIR) single-doc-year-target
```

Similar as the TETML extraction, pages without actual content are excluded when extracting text with TET.

After removing any whitespace and digits around form feeds (i.e., printed page numbers), [cutter](https://pub.cl.uzh.ch/wiki/public/cutter/start) tokenizes the extracted text whereby the isolated punctuation is used to determine the end of a sentence naively. Specifically, the sentence segmentation works implicitly by splitting at the following symbols `.;?!` if they are not considered as part of a token (i.e., abbreviations). Moreover, very long sentences are split after 250 tokens (e.g., list of names). Neither the new line characters `\n` nor periods `.` are a good indication due to OCR issues. 

Because of the current requirements of the script to align documents (see below), the segmented articles of a particular year are concatenated into a single document (e.g., `de_1849_all.txt`). This document includes meta-information for restoring the original articles. Specifically, the document includes the path to the original article, markers for the end of an article (`.EOA`) and the end of a book (`.EOB`), which corresponds to all articles within a single year.  The logical structure of this document is as follows:
```
PATH TO PUBLICATION DIRECTORY
    PATH TO ARTICLE 1
         CONTENT
    .EOA
    PATH TO ARTICLE 2
         CONTENT
    .EOA
.EOB
```

The following is a minimal example of a single document for the year 1849.
```
data_text/FedGazDe/1849/
data_text/FedGazDe/1849/12/22/10000234.cuttered.sent.txt
Schweizerisches Bundesblatt .
Nro 33. Samstag , den 22. Dezember 1849 .
Die vom Staat New-York zum Schutz aller Einwanderer besonders eingesetzte Kommisfion an die deutscheu Einwanderer welche in New-York landen .
.EOA
.EOB
```

**Todo**

The concatenation is undesirable as it is inflexible and makes the debugging unnecessarily harder. We should modify the alignment script to work on a per article-basis instead of a single file.

Moreover, the naive sentence segmentation should be replaced with a specific tool that considers some golden rules when splitting sentences like [pySBD](https://github.com/nipunsadvilkar/pySBD).

### Aligning documents
For the alignment of the articles across languages, an improved version of an in-house script written by Chantal Amrhein is employed, which leverages the [Bleualign](https://github.com/rsennrich/Bleualign) for sentences to the level of documents. 

The script is designed to align parallel articles, meaning a text and its direct translation, without having a robust identifier that links both versions. Using an automatic translation of one of the texts, Bleualign finds article pairs by computing their similarity (modified BLEU score). Therefore, an MT-system translates the document of year-wise concatenated articles into the target language before doing the actual document alignment (for the training of the MT-system, see below).

The script takes a file pair comprising all articles of a particular in a source and target language, as well as a translated version of the source text. For each list of candidates alignments consisting of a translated source and the target files, a dynamic programming approach maximizes the BLEU score overall found article alignments. The approach works efficiently and leverages the strong temporal correlation between languages as compared to a naive document-by-document comparison. 

Since some pairs should not be aligned but still contribute (minimally) to the overall BLEU score, all pairs returned by the dynamic programming approach are re-evaluated. If the BLEU score is above a certain threshold, the pair is accepted as parallel articles. Else, a combination of the similarity in length and the matching numbers in the articles determines whether the articles should still be considered parallel articles. Finally, if the pair is not decided to be parallel, the script checks whether they could be similar articles using a tf/idf vectorizer. However, the articles which correspond only to some degree are not considered in the parallel corpus.

In the dynamic programming approach, the memory consumption follows a quadratic function. For years with a few thousand articles, this technique causes problems. Thus, the years are processed batch-wise. Repeatedly, a batch of 500 articles in the source language is compared to all target articles for a single year. As this may lead to 1:n alignments meaning that multiple source articles are assigned to the same target article, an additional filtering step is carried out after the dynamic programming matching to ensure 1:1 alignments. Thus, only the alignment with the highest BLEU-score for a particular target article is kept.

This script outputs an `.xml` file with containing links to the found parallel documents as well as a `_stats.tsv` file comprising statistics of the alignment process and descriptive statistics of the corpora. Subsequently, the XML is converted into a TSV-file that is more suitable as an input for the sentence alignment process. 



#### Statistics and Evaluation of Document Alignments

For the evaluation of the precision of the found parallel documents, a human needs to evaluate the alignments as an automated evaluation is not appropriate. The script `eval_alignment.py` speeds up the evaluation process by outputting a standardized evaluation schema. The schema includes metadata as well as two commands to compare the heads and tails of randomly selected documents. 

The statistics about the number of documents per year and ratio of alignments in addition to some other numbers (e.g., number of tokens and sentences) can be found here: `data_alignment/de_fr_overview_stats_alignment.tsv`



#### Training and translating with Moses MT-system
In principle, any machine translation system could be used to translate articles from a source into a target language. To improve the recall and the precision of alignments, a custom system is trained. As a good translation is not a goal in itself in our case, a simple Moses model is trained on lowercased corpora of [bilingwisslc](https://www.zora.uzh.ch/id/eprint/54761/) and [JRC-Acquis](http://opus.nlpl.eu/JRC-Acquis.php). The choice of these corpora accounts for the legal focus of text in the context of Switzerland.

The training data is stored here: `mt_moses/train_de_fr/`

### Sentence Alignment
As for the construction of the parallel UN corpus, [bleu-champ](https://github.com/emjotde/bleu-champ) is used to align sentences of the parallel documents. 

The sentence alignment works on the level of a single article and requires line-wise correspondence across source, target, and translated files. Due to the year-translation, the concatenated translated files are split again before written into memory for faster processing. 

The tab-separated output file of bleu-champ is then concatenated across years and split into two separate files, one comprising the parallel sentences in the source language and the other in the target language.

### Parallel corpus
The parallel corpus German-French consists of two line-aligned files that also preserves the boundaries of documents. To mark the document boundary, the following separator is used, which refers to the original file: 

- Generic separator: `.EOA data_text/de/YEAR/YEAR-MONTH-DAY/DOCID.cuttered.sent.txt`
- Example separator: `.EOA data_text/de/1878/1878-12-21/10010179.cuttered.sent.txt`

Due to the many errors in the OCR process and well as non-natural language elements like tables or lists, the parallel corpus needs to be filtered. The process makes use of heuristics similar to the [cleaning script of Moses](https://github.com/moses-smt/mosesdecoder/blob/master/scripts/training/clean-corpus-n.perl) and keeps only sentence pairs that fulfil the following filtering criteria:

- number of tokens between 5 and 150
- number of characters between 30 and 700
- character length ratio between source and target sentence is not higher than 1.6
- digit ratio wtr to string length is not higher than 0.2

The filtering process is simply based on structural criteria of the sentences leaving semantic aspects aside. Thus, the quality of the sentence pairs is far from optimal given some forced alignments due wrong document alignments. Moreover, corpus contains the tokenized text rather than the original text.

The resulting corpus contains more than 3.5 million sentences from over 53k documents and is stored in two files:

- `data_alignment/de_fr_sent_parallel_filtered.de`

- `data_alignment/de_fr_sent_parallel_filtered.fr`



**Todo**

Use the [LASER toolkit](https://github.com/facebookresearch/LASER) or a similar tool to improve the quality of the alignments. However, it is not yet known how these neural approaches perform on texts with many OCR issues.  



### Bilingual Embeddings

The parallel corpus of the Federal Gazette in German and French is used to train bilingual embeddings. The bilingual embeddings are used on the [impresso platform](https://impresso-project.ch/app/) to improve the information retrieval across languages.

To give the embeddings a contemporary twist and account for the manifold distortions due to OCR errors, our corpus is concatenated with the [Europarl](http://opus.nlpl.eu/Europarl.php) corpus. Before concatenating, we tokenize Europarl with cutter to ensure homogeneous tokenization in the entire training data. 

After experimenting with various preprocessing settings, the final training data is preprocessed as follows:

- keep only alpha-numeric tokens
- lowercase
- replace any digits with `0`
- minimum word count of 5 (`UNK ` symbol for words that occur less than 5 times)

The bilingual embeddings are trained with [multiVec](https://github.com/eske/multivec). The procedure builds on skip-gram of word2vec while simultaneously training on the parallel sentences to encode words in a shared semantic space. 

The pipeline implements embeddings with the size of 100, 150, 300 following a similar training routine. As for our purpose, the semantic information is more critical as the syntactic, a large window of 10 tokens is used. multiVec trains for 20 epochs. Moreover, only words are kept that occur at least 10 times. Other parameters are standard.

We decided on the multiVec and the these parameters after extensive experimentation with various settings. As you can see in our brief [report](experiments/experiments_multilingual_embeddings.md) , the older method multiVec consistently outperforms the supposedly state-of-the-art of FastText embeddings aligned with MUSE.


### Phrase Extraction
There are some experiments to detect phrases to allow embedding multi-word expressions. However, the results are currently not used.

- gensim phrase extraction by scoring with NPMI: `lib/phrase_detection.py`
- spaCy NER: `lib/processing_spacy.py`

