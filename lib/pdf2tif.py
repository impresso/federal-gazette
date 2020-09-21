#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Create Bash scripts to extract and rename TIF images from scanned documents
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
import pandas as pd

RENAME = """
a=1
for i in `ls -v {0}/*.tif`; do
  new=$(printf "{1}-p%04d.tif" "$a")
  mv "$i" "{0}/$new"
  a=$((a+1))
done
"""


def parse_args():
    """Parse the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        action="store",
        dest="f_in",
        help="input file with tab-separated metadata",
    )

    parser.add_argument(
        "-t",
        "--tet",
        required=True,
        action="store",
        dest="f_tet",
        help="output file into which tet commands are written",
    )

    parser.add_argument(
        "-r",
        "--rename",
        required=True,
        action="store",
        dest="f_rename",
        help="output file into which renaming commands are written",
    )

    return parser.parse_args()


def create_bash_scripts(fname_in, fname_tet, fname_rename):
    """
    Write two Bash scripts to extract and rename the tif images respectively.
    The script uses the canonical schema, used in the Impresso project.
    """

    df = pd.read_csv(fname_in, sep="\t", parse_dates=["issue_date"])

    with open(fname_tet, mode="w") as f_tet, open(fname_rename, mode="w") as f_rename:
        # remove potential existing data of this newspaper
        trg_dir = "/".join(df.loc[0, "canonical_dir_tif"].split("/")[:2])
        # os.system("rm -rf " + trg_dir)
        f_tet.write("rm -rf " + trg_dir + "\n")

        # Restrict to period for which scanned documents with OCR exists.
        # Starting from 22 June 1999, documents are fully digital
        for i, row in df[df.issue_date < "1999-06-22"].iterrows():

            mkdir = "mkdir -p " + row["canonical_dir_tif"]
            # os.system(mkdir + "\n")
            f_tet.write(mkdir + "\n")

            # create tif files from pdf if document has a length of 1 at minimum
            if row["page_count_full"] > 0:
                tet = "tet --targetdir {} --image --lastpage {} {}".format(
                    row["canonical_dir_tif"], row["page_count_full"], row["pdf_path"]
                )
                # os.system(tet + "\n")
                f_tet.write(tet + "\n")

            # rename the created files according to the canonical scheme after each day (change of directory)
            stem = "-".join(row["canonical_dir_tif"].split("/")[1:])
            try:
                if row["canonical_dir_tif"] != df.loc[i + 1, "canonical_dir_tif"]:
                    # os.system(rename.format(row["canonical_dir_tif"], stem) + "\n")
                    rename_issue = RENAME.format(row["canonical_dir_tif"], stem)
                    f_rename.write(rename_issue + "\n")

            except KeyError:
                # do also the renaming after the last article
                # os.system(rename.format(row["canonical_dir_tif"], stem) + "\n")
                rename_issue = RENAME.format(row["canonical_dir_tif"], stem) + "\n"
                f_rename.write(rename_issue + "\n")


def main():
    args = parse_args()

    create_bash_scripts(args.f_in, args.f_tet, args.f_rename)


################################################################################
if __name__ == "__main__":

    main()
