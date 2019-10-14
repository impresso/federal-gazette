#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""

"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
import pandas as pd
import os


def parse_args():
    """parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        action="store",
        dest="f_in",
        help="input file with tab-separated metadata",
    )

    return parser.parse_args()


def extract_tif_via_bash(f_in):
    """
    Extract tif images from all the pdfs and rename them according to the canonical naming scheme.
    The Bash commands are assembled in Python and written to stdout.
    """

    rename = """
    a=1
    for i in `ls -v {0}/*`; do
      new=$(printf "{1}-p%04d.tif" "$a")
      mv "$i" "{0}/$new"
      a=$((a+1))
    done
    """

    df = pd.read_csv(f_in, sep="\t", parse_dates=["issue_date"])

    # remove potential existing data of this newspaper
    trg_dir = "/".join(df.loc[0, "canonical_dir_tif"].split("/")[:2])
    os.system("rm -rf " + trg_dir)

    for i, row in df.iterrows():

        mkdir = "mkdir -p " + row["canonical_dir_tif"]
        os.system(mkdir + "\n")

        # create tif files from pdf if document has a length of 1 at minimum
        if row["page_count_full"] > 0:
            tet = "tet --targetdir {} --image --lastpage {} {}".format(
                row["canonical_dir_tif"], row["page_count_full"], row["pdf_path"]
            )
            os.system(tet + "\n")

        # rename the created files according to the canonical scheme after each day (change of directory)
        stem = "-".join(row["canonical_dir_tif"].split("/")[1:])
        try:
            if row["canonical_dir_tif"] != df.loc[i + 1, "canonical_dir_tif"]:
                os.system(rename.format(row["canonical_dir_tif"], stem) + "\n")
        except KeyError:
            # do also the renaming after the last article
            os.system(rename.format(row["canonical_dir_tif"], stem) + "\n")


def main():

    # parse arguments
    args = parse_args()

    extract_tif_via_bash(args.f_in)


################################################################################
if __name__ == "__main__":

    main()
