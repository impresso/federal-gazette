#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""

"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import sys


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
      new=$(printf "{1}-%04d.tif" "$a")
      mv -i -- "$i" "{0}/$new"
      let a=a+1
    done
    """

    # remove potential data
    trg_dir = df.loc[0, "canonical_dir_tif"].split("/")[0]
    sys.stdout.write("rm -rf" + trg_dir)

    df = pd.read_csv(f_in, sep="\t", parse_dates=["issue_date"])

    for i, row in df.iterrows():

        mkdir = "mkdir -p " + row["canonical_dir_tif"]
        sys.stdout.write(mkdir + "\n")

        # create tif files from pdf
        tet = "tet --targetdir {} --image --lastpage {} {}".format(
            row["canonical_dir_tif"], row["page_count_full"], row["pdf_path"]
        )
        sys.stdout.write(tet + "\n")

        # rename the created files according to the canonical scheme after each day (change of directory)
        stem = "-".join(row["canonical_dir_tif"].split("/")[1:])
        try:
            if row["canonical_dir_tif"] != df.loc[i + 1, "canonical_dir_tif"]:
                sys.stdout.write(rename.format(row["canonical_dir_tif"], stem) + "\n")
        except KeyError:
            # do also the renaming after the last article
            sys.stdout.write(rename.format(row["canonical_dir_tif"], stem) + "\n")


def main():

    # parse arguments
    args = parse_args()

    f_db = args.f_in
    extract_tif_via_bash(f_db)


################################################################################
if __name__ == "__main__":

    main()
