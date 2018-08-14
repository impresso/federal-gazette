#!/usr/bin/python3
"""
Script to produce tab-separated info files from federal web sites.

{'article_docid': '10029899', 'issue_html': 'www.admin.ch/opc/de/federal-gazette/1926/index_50.html', 'issue_date': '1926-12-15', 'volume_language': 'de', 'issue_path': 'www.admin.ch/opc/de/federal-gazette/1926/index_50.html', 'issue_page_first': 817, 'issue_number': '50', 'article_page_first': 817, 'article_title': 'Botschaft des Bundesrates an die Bundesversammlung betreffend die Ausrichtung von Teuerungszulagen an das Bundespersonal für das Jahr 1927. (Vom 6. Dezember 1926.)', 'volume_number': 'II', 'issue_page_last': 896, 'article_pdf_url': 'http://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10029899'}


"""

import sys, codecs,re
import os
import pandas as pd
from optparse import OptionParser
from random import shuffle
import magic

from de_lemmatizer  import STOPWORDS, STOPWORDPOS, FREQDIST , LEMMATIZATION,\
     read_freq_file,  read_lemma_file,read_json_file


__author__ = "Simon Clematide"
__email__ = "siclemat@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2018"
__status__ = "development"



sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)

OPTIONS = {}

def main(args):
    """
    Given a main html index file from www.admin.ch  convert all HTML files to tsv files
    :param input_dir: directory containing tetml files
    :param row_hint: define which Element in the XML tree contains one text row
    :return:
    """
    pass

if __name__ == '__main__':

    parser = OptionParser(
        usage = '%prog [OPTIONS] [ARGS...]',
        version='%prog 0.99', #
        description='Download gazette federal files',
        epilog='Contact simon.clematide@uzh.ch'
        )
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')
    parser.add_option('-m', '--mode',
                      action='store', dest='mode', default='wget',type=str,
                      help='mode: more (%default)')

    parser.add_option('-O', '--old_frequency_file',metavar="FILE",
                      action='store', dest='old_frequency_file', default=None,
                      help='old_frequency_file  (%default)')
    parser.add_option('-N', '--new_frequency_file',metavar="FILE",
                      action='store', dest='new_frequency_file', default=None,
                      help='new_frequency_file  (%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)

    main(args)
