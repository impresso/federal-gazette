#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Create textfile with all with the filenames of aligned articles
given the xml-alignment-file and the directory with the translated
source files (corresponding articles need to have identical names)
"""

# imported modules
from lxml import etree
import argparse


# global variables
# parsing xml with utf-8 encoding and removing blank text
parser = etree.XMLParser(remove_blank_text=True, encoding="utf-8")


################################################################################


def parse_args():
    """parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i", "--input", required=True, action="store", dest="f_in", help="input file"
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        action="store",
        dest="f_out",
        help="output file",
    )
    parser.add_argument(
        "-t",
        "--dir_trans",
        required=True,
        action="store",
        dest="dir_trans",
        help="translation dir",
    )

    return parser.parse_args()


def read_src_translation(f_trans):
    with open(f_trans) as f:
        lines = f.readlines()
    # remove header "input_dir" and footer ".EOB"
    lines = lines[1:-1]
    articles = "\n".join(lines).split(".EOA")

    # map source file name (first line) to its translated text (subsequent lines)
    trans_articles = {art[0]: art[1:] for art in articles}

    return trans_articles


def import_alignments(f_align):
    """read the alignment pairs"""

    xml = etree.parse(f_align, parser).getroot()

    alignments = {}

    # collection of aligned src and trg filename
    for collection in xml.xpath("//linkGrp"):
        # files = collection.get('xtargets').split(';')
        # langs = collection.get('lang').split(';')

        for article in collection.getchildren():
            src, trg = article.get("xtargets").split(";")
            alignments[src] = trg

    return alignments


def main():

    # parse arguments
    args = parse_args()

    f_align = args.f_in
    f_out = args.f_out
    dir_trans = args.dir_trans

    # src_translations = read_src_translation(f_trans)

    alignments = import_alignments(f_align)

    with open(f_out, "w") as f:
        for src, trg in alignments.items():
            # example path: data_text/FedGazFr/1849/07/07/10055445.cuttered.sent.txt
            # set relative path to translation file
            f_parts = src.split("/")
            year = f_parts[-4]
            f_trans = f_parts[-1]
            trans = "/".join([dir_trans, year, f_trans])

            line = "\t".join([src, trg, trans])
            f.write(line + "\n")


################################################################################
if __name__ == "__main__":

    main()
