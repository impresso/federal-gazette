#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Extend tsv-file with more metadata (file to pdf, number of pdf pages)
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
import pandas as pd


def parse_args():
    """Parse the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input",  required=True,
                        action="store", dest="f_in", help="input file")
    parser.add_argument("-o", "--output",  required=True,
                        action="store", dest="f_out", help="output file")

    return parser.parse_args()


def main():

    args = parse_args()
    f_in = args.f_in
    f_out = args.f_out

    df = pd.read_csv(f_in,  sep='\t')
    lang = f_in.split('.')[0].split('-')[-1]  # parse language id

    df_pages = pd.read_csv(lang+'.pages.tsv', sep='\t', header=None, dtype='object')
    df_pages = df_pages.rename(columns={0: 'pdf_path', 1: 'page_count'})

    # derive file path
    df['pdf_path'] = 'data_pdf/' + lang + '/' + df['issue_date'].str.split(
        '-').str[0] + '/' + df['issue_date'] + '/' + df['article_docid'] + '.pdf'
    df = pd.merge(left=df, right=df_pages, how='left', on='pdf_path')

    df.sort_values(by=['issue_date', 'article_page_first', 'article_docid'], inplace=True)

    df.to_csv(f_out,  sep='\t')


################################################################################
if __name__ == "__main__":
    main()
