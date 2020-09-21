# Federal Gazette Corpus 

The [Federal Gazette](https://www.admin.ch/gov/de/start/bundesrecht/bundesblatt/erlaeuterungen-zum-bundesblatt.html) is journal published by the Swiss Government. The journal is political newsletter concerned with resolutions and laws of Swiss Confederation. First published in 1849, briefly after the foundation of the Swiss Federal State, it is provided in the following official languages:

- German ("Bundesblatt") 
- French ("Feuille fédérale")
- Italian ('Foglio federale')

## General structure of the federal gazette publications
 - The federal gazette has one or more volumes (German "Band") per year (numbered from I by roman numbers). Before 1998, each volume started with page number 1.
 - Each volume consists of several issue (German "Heft") (numbered from 1 by arabic numbers within each volume). 
 - Each issue consists of several articles  In earlier editions, more than one article can appear on a single page. 

The schema for page numbering in volumes changes starting with the year 1998. Before 1 January 1998, the page numbering of each volume starts from 1. 
The index of keywords is published separately for each volume (and each text reference included the volume number and the page number, for instance, <https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10046396>).
After 1 January 1998 the pages of a whole year are numbered consecutively and the index of keywords directly references the (unique) page numbers of a volume (<https://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10054877>).

Starting from 22 June 1999, there is no volume organization anymore.

Sometimes the official document does not contain anything due to some data privacy. For instance, <https://www.admin.ch/opc/de/federal-gazette/2016/1506.pdf> or <https://www.admin.ch/opc/de/federal-gazette/2015/1376.pdf>.


## Documentation of Corpus Download and Processing
The download and and build process of the corpus is defined via `make` targets in the file `Makefile`.
The following documentation describes the different steps on a conceptual level and with example calls of `make`.


### Downloading the HTML index files with all meta information for a given language and time period

We use `wget` to download all html files with relevant information into a folder structure under `www.admin.ch`.
The download is throttled by default to `32k`. This results in a decent behavior without blocking. Additionally, the wget call makes sure that files that are already locally available and where no newer version is online are not downloaded again.

The make target `download-index-all` downloads all necessary files for all languages. 

Example call for specific download of French federal gazette issues from 1849 to 2017:

```bash
YEARS_START=1849 YEARS_END=2017 make dl-fr
```

#### Complications

The year 1999 is split between material from the Bundesarchiv and the Federal Council. Therefore, there are two index files from 1999. `indexbar.html` from the Bundesarchiv and `index.html` from the Federal Council.

### Extracting the meta-information from the index files
All information about each article is stored in a tabulator-separated text file. For instance, `article-info-FedGazDe.tsv` for all German articles. 
The script `lib/gf_html2info.py` compiles this information from the HTML index files. The make target `article-info-all-target` compiles all 3 languages.

```bash
make article-info-all-target
```

#### Downloading the PDF files
1. Each file from the Bundesarchiv has a unique numeric article ID `NNNNNNNNN`. 
2. Each file from the Federal Council gets an unofficial unique article ID consisting of the combination of year and first page: `YYYY_PAGE`.

This results in a unique identifier as each article starts on its own page in the time period starting from 1999. The article identifier is used as file name, while the is organized in a separate directory as follows:

`data_pdf/{JOURNAL_NAME}/{YYYY}/{MM}/{DD}/{ARTICLEID}.pdf `

We use abbreviated journal names per language

- FedGazDe (German)
- FedGazFr (French)
- FedGazIt (Italian)

The download process is a two-step process:
 1. The script `lib/gf_download.py` reads the `article-info-FedGazDe.tsv` and checks whether the file is already downloaded. If not, then the corresponding shell commands are emitted. The make target `download-all-target` creates the shell files `download-FedGazDe-target.bash`.
 2. After assembling the file with the shell commands, the file  `download-FedGazDe-target.bash`  is run by the same make recipe.

A download limit rate of 500kb seems reasonable for throttling the process.

#### Conversion from PDF to TETML



#### Conversion from PDF to JPEG2000



#### Evaluation of Article segmentation



## Produce canonical format and ingest data 

data-ingest-all-target



### Impresso canonical filename specification

Following the [Impresso specifications](https://github.com/impresso/impresso-schemas), the canonical files are named as follows:

 - German
   - FedGazDe-YYYY-MM-DD-a-00001.json
 - French
   - FedGazFr-YYYY-MM-DD-a-00001.json
 - Italian
   - FedGazIt-YYYY-MM-DD-a-00001.json


