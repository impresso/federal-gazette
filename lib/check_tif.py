#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Check existence of canonical tif file
"""

import sys
import os
import pandas as pd


def check_file_exist(fname):
    return os.path.isfile(fname)


def check_canonical_archive(fname):
    df = pd.read_csv(fname, sep="\t", parse_dates=["issue_date"])
    df["exist"] = df.canonical_path_tif.apply(check_file_exist)

    print(df.exist.describe())
    print(df.groupby(["year", "exist"])["exist"].count())

    fout = fname.split(".")[0] + "_tif_stats.csv"
    df.groupby(["year", "exist"])["exist"].count().to_csv(fout)


def main():
    check_canonical_archive(sys.argv[1])


if __name__ == "__main__":
    main()
