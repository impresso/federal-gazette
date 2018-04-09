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
    if len(args) == 1:
        records = pd.read_table(args[0], low_memory=False).to_dict('records')
        shuffle(records) # load balancing as some part comes from Bundesarchiv and others from federal office
        output_wget_commands(records)

def output_wget_commands(records):
    downloads = 0
    nodownloads = 0
    MKDIRCMD = ' mkdir -p {OUTPUTDIR}\n'
    WGETCMD = ' wget --limit-rate=500k {OPTIONS} "{URL}" -O {OUTPUTDIR}/{OUTPUTFILE}\n'
    info = {}
    for r in records:
        info['URL'] = r['article_pdf_url']
        if 'amtsdruckschriften' in info['URL']: # Big PDF files need this parameter for download
            info['URL'] += '&action=open'
        info['OPTIONS'] = ''
        info['OUTPUTDIR'] = os.path.join(OPTIONS.get('data_dir'),r['volume_language'],r['issue_date'][:4],r['issue_date'])
        info['OUTPUTFILE'] = r['article_docid']+'.pdf'
        command = " "
        if not os.path.exists(info['OUTPUTDIR']):
            command = MKDIRCMD.format(**info)
        pdffile = os.path.join(info['OUTPUTDIR'],info['OUTPUTFILE'])
        if not os.path.exists(pdffile) or os.stat(pdffile).st_size == 0 or not 'pdf' in magic.from_file(pdffile, mime=True):
            command += WGETCMD.format(**info)
            downloads += 1
        else:
            print('#INFO-FILE-EXISTS',pdffile, file=sys.stderr)

            nodownloads += 1
        if not command.isspace():
            print(command)
    print('#STATS-FILES-TO-DOWNLOAD',downloads,file=sys.stderr)
    print('#STATS-FILES-NOT-TO-DOWNLOAD',nodownloads,file=sys.stderr)

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
                      help='output wget: Emit wget commands for missing files (%default)')
    parser.add_option('-D', '--data_dir',
                      action='store', dest='data_dir', default='data_pdf',type=str,
                      help='data dir  (%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)

    main(args)
