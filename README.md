# Federal Gazette Corpus 

The [Federal Gazette](https://www.admin.ch/gov/de/start/bundesrecht/bundesblatt/erlaeuterungen-zum-bundesblatt.html) is a journal published by the Swiss Government. The journal is a political newsletter concerned with resolutions and laws of the Swiss Confederation. First published in 1849, briefly after the foundation of the Swiss Federal State, it is provided in the following official languages:

- German ("Bundesblatt") 
- French ("Feuille fédérale")
- Italian ("Foglio federale")

Although Italian data is downloaded it is not further processed. Moreover, the Italian Federal Gazette is only available starting from 1971.

## General structure of the Federal Gazette publications
 - The Federal Gazette has one or more volumes (German "Band") per year (numbered from `I` by roman numbers). Before 1998, each volume started with page number `1`.
 - Each volume consists of several issues (German "Heft") (numbered from `1` by Arabic numbers within each volume). 
 - Each issue consists of several articles. In earlier editions, more than one article can appear on a single page. 

The schema for page numbering in volumes changes starting with the year 1998. Before 1 January 1998, the page numbering of each volume starts from `1`. Moreover, the earlier period may contain in-page article segmentations meaning that a new article begins on the same page where the previous article ends. In these cases, the page comprising the boundary is redundantly assigned to the PDFs of both articles. For the sake of consistency, such pages need additional processing to define the correct article boundary.

The index of keywords is published separately for each volume. Moreover, each text reference includes the volume number and the page number. For instance: <https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10046396>

After 1 January 1998, the pages of a whole year are numbered consecutively, and the index of keywords directly references the (unique) page numbers of a volume. For instance: <https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10054877>

Starting from 22 June 1999, there is no volume organization anymore.

Sometimes the official document does not contain anything due to some data privacy. For instance, <https://www.admin.ch/opc/de/federal-gazette/2016/1506.pdf> or <https://www.admin.ch/opc/de/federal-gazette/2015/1376.pdf>.

## Installation and preparatory steps

### Quick setup


```bash
git clone https://github.com/impresso/federal-gazette.git
cd federal-gazette
pipenv --python 3.6
```

### pipenv

This repository is tested for Python 3.6 only. Use the pipenv command from above to set up a virtual environment for this particular Python version and install the necessary packages. 

`pipenv` goes beyond the capabilities of the combination of `pip` and `venv` replicates an identical working environment using the `Pipfile`. 

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
- Moses: http://www.statmt.org/moses/

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

#### ToDo: Run entire Pipeline 

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

### Downloading the HTML index files with all metadata for a given language and time period

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
All information about each article is stored in a tab-separated text file. For instance, `article-info-FedGazDe.tsv` for all German articles. 
The script `lib/gf_html2info.py` compiles this information from the HTML index files. The make target `article-info-all-target` compiles all three languages.

```bash
make article-info-all-target
```

#### Downloading the PDF files

1. Each file from the Bundesarchiv has a unique numeric article ID `NNNNNNNNN`. 
2. Each file from the Federal Council gets an unofficial unique article ID by concatenating the year and the first page: `YYYY_PAGE`.

This results in a unique identifier as each article starts on a separate page in the time period starting from 1999. The article identifier is used as file name, while the data is organized by newspaper and date as follows:

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

## Canonization and ingestion of data 

The [Impresso-text-acquisition](https://impresso.github.io/impresso-text-acquisition/) package provides several importers, among them the `tetml-importer` `fedgaz-importer`. These importers parse the TETML files on a per issue basis and transforms them into the [canonical JSON format](https://github.com/impresso/impresso-schemas) required by the Impresso platform. A issue consists of articles published on the same day.

Specifically, the importer yields a single JSON file per year, comprising an overview of all published issues, along with a JSON for each page, which contains the actual content. The coordinates are computed relative to the size of the TIF image (actual scan) whereby a specific text element gets the coordinates by drawing a new bounding box around all lower-level elements (region > paragraphs > lines > words).

To perform a logical article segmentation, the `fedgaz-importer` has to be used instead of the generic `tetml-importer`. This custom importer inherits most of its class methods from the generic importer, however, it accounts for the specificities of the FedGaz data. Specifically, it features a heuristic search of the title on the first page of the subsequent article to set exact article boundaries ([see article segmentation](#anchors-logical-article-segmentation)). The remainder on this page belonging to the previous article is then moved into a separate region and assigned to the correct article. This importer may be well used for other resources that need a post hoc logical article segmentation.

### Ingest Text Data

The importer performs the canonization of the textual data and its upload to s3 in a single step. We can start the import process by calling the following recipe:

```bash
make data-ingest-FedGazDe
```

To upload the data to s3, the following environment variable needs to be set:

```bash
export SE_ACCESS_KEY=X
export SE_SECRET_KEY=X
```

### Ingest Image Data

The upload of the canonical images is separated from the textual data and may be started with the following recipe:

```bash
make jp2-ingest-FedGazDe
```

We use `rclone` instead of `s3cmd` as it allows parallel transfers and is also more robust when processing big chunks of data. 

## Logical Article Segmentation

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
