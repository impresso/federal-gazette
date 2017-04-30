## Monolingual download and metadata 

Each year has an HTML overview.

Each overview links to each PDF file of each volume (modulo segmentation errors).

Each overview has a title for each PDF file.

A tabseparated document metadata/{LANG}-dl-meta.tsv
 - for each PDF document, we collect the following information
   1. URL
   2. date of download 
   3. size in bytes
   4. relative storage path according to the schema BASEDIR/YYYY-MM-DD/FILENAME


   
=======
# Facharbeit
Python-Scripts der Facharbeit

Scraping:
Bundesblatt_scraper_1849-1999.py
Bundesblatt_scrape_1999-2016.py
download_big_pdfs.py

Preprocessing:
preprocess_titles.py

Translation:
mosesclient_titles.py

Alignment:
bleuchamp.py
check_alignment_titles.py

Statistics:
search_short_tr.py
alignment_statistics.py
