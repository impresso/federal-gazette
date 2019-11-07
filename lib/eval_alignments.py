#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Evaluation of document pairs that are considered parallel
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"

import glob
import pandas as pd
import xml.etree.ElementTree as ET
import re
import random
import argparse


def parse_args():
    """Parse the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--dir_in",
        required=True,
        action="store",
        dest="dir_in",
        help="input directory where the '*alignments.xml' are stored",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        action="store",
        dest="f_out",
        help="name of output file",
    )
    parser.add_argument(
        "-s",
        "--samples",
        required=False,
        default=10,
        action="store",
        dest="n_samples",
        help="number of samples per year",
    )

    return parser.parse_args()


def create_evaluation_schema(fname_out, dir_in, options):
    dfcols = [
        "year",
        "index",
        "src",
        "trg",
        "method",
        "score",
        "script_head",
        "scrip_tail",
        "eval_head",
        "eval_tail",
        "comment",
    ]

    df = pd.DataFrame(columns=dfcols)

    for fname in glob.glob(dir_in + "*alignments.xml"):
        etree = ET.parse(fname)
        root = etree.getroot()

        n_elements = len(list(root.iter(tag="link")))

        try:
            samples = random.sample(range(0, n_elements), options.n_samples)
        except ValueError:
            print(
                "Sample size is larger than number of alignments. {} will be skipped".format(
                    fname
                )
            )
            continue

        for index, item in enumerate(root.iter(tag="link")):
            if index in samples:
                src, trg = item.get("xtargets").split(";")
                year = re.search(r"/(\d{4})/", src).group(1)
                method = item.get("method")
                score = item.get("score")
                script_head = (
                    "diff -W 200 -y <(head -n 30 " + src + ") <(head -n 30 " + trg + ")"
                )
                script_tail = (
                    "diff -W 200 -y <(tail -n 30 " + src + ") <(tail -n 30 " + trg + ")"
                )

                attr = [
                    year,
                    index,
                    src,
                    trg,
                    method,
                    score,
                    script_head,
                    script_tail,
                    "",
                    "",
                    "",
                ]

                df = df.append(pd.Series(attr, index=dfcols), ignore_index=True)

    df = df.sort_values(by=["year"]).reset_index(drop=True)

    df.to_csv(fname_out, sep="\t")

    print(f"Evaluation successfully created: {fname_out}")


def main():

    args = parse_args()
    create_evaluation_schema(args.f_out, args.dir_in, args)


################################################################################
if __name__ == "__main__":
    main()
