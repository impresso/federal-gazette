#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Extend the dataset with more metadata and perform a heuristic detection of
multiple instances of a single page due to in-page article segmentation.
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"

import argparse
import pandas as pd
import numpy as np


def parse_args():
    """Parse the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i", "--input", required=True, action="store", dest="f_in", help="input file"
    )
    parser.add_argument(
        "-o", "--output", required=True, action="store", dest="f_out", help="output file",
    )

    parser.add_argument(
        "-p",
        "--dir_pdf",
        required=True,
        action="store",
        dest="dir_pdf",
        help="source directory for pdf",
    )
    parser.add_argument(
        "-t",
        "--dir_tif",
        required=True,
        action="store",
        dest="dir_tif",
        help="destination directory for canonical tif files",
    )
    parser.add_argument(
        "--pages",
        required=True,
        action="store",
        dest="f_pages",
        help="input file that contains information about the pages for all pdf",
    )

    return parser.parse_args()


def set_empirical_page_count(df, can_src_name, dir_pdf, f_pages):
    df_pages = pd.read_csv(f_pages, sep="\t", header=None)
    df_pages = df_pages.rename(columns={0: "pdf_path", 1: "page_count"})

    # derive file path
    df["pdf_path"] = (
        dir_pdf
        + "/"
        + can_src_name
        + "/"
        + df["issue_date"].astype(str).str.replace("-", "/")
        + "/"
        + df["article_docid"].astype(str)
        + ".pdf"
    )
    df = pd.merge(left=df, right=df_pages, how="left", on="pdf_path")

    # subtract 1 from page count for every article published until 15.06.1999.
    # reason: last page contains only meta-information in this period.
    df.loc[df["issue_date"] <= "1999-06-15", "page_count"] = df.loc[
        df["issue_date"] <= "1999-06-15", "page_count"
    ].map(lambda x: x - 1)

    return df


def find_overlapping_pages(df):
    """
    Finds multiplied instances of an identical page shared by two subsequent
    articles due to in-page article segmentation.

    The heuristic leverages the assumption that such overlap can only occur
    within an issue of a particular day. However, supplements are excluded from
    this heuristic as the original metadata is not consistent.
    The results of this procedure are used downstream to perform a heuristic
    article segmentation.
    """

    df["page_count_full"] = df["page_count"]
    df["supplement"] = df["article_title"].str.contains(r"inserate|beilage", case=False)

    df["article_page_first_next"] = df["article_page_first"].shift(-1)
    df["supplement_next"] = df["supplement"].shift(-1)

    groups = df.groupby("issue_date")

    for _, group in groups:

        n_articles = len(group)

        for group_pos, (idx, article) in enumerate(group.iterrows()):

            art_start = article["article_page_first"]
            art_length = article["page_count"]
            art_end = art_start + art_length - 1

            art_next_start = article["article_page_first_next"]
            art_next_supplement = article["supplement_next"]

            issue_end = article["issue_page_last"]

            # identifying two instances of a single page,
            # shared between two subsequent articles

            # the heuristic presumes that supplements never share pages with
            # a previous article as the underlying metadata is incorrect
            # in the majority of cases

            if group_pos + 1 < n_articles and art_end == art_next_start:

                if not (
                    # not considering supplements that are defined as a one pager at the end of an issue
                    art_next_start == issue_end
                    # not considering any supplements heuristically identified by title
                    or art_next_supplement
                ):

                    df.loc[idx, "page_count_full"] = art_length - 1

    df["pruned"] = np.where(df.page_count_full != df.page_count, True, False)

    # remove temporary columns
    df.drop(["article_page_first_next", "supplement_next"], axis=1, inplace=True)

    return df


def set_canonical_numbering(df):
    """
    Set first and last pages according to canonical naming schema of impresso,
    which enumerates page numbers within an issue published on a single day.
    """

    # set to the last full page
    df["canonical_page_last"] = df.groupby(["issue_date"])["page_count_full"].apply(
        lambda x: x.cumsum()
    )
    df["canonical_page_first"] = df["canonical_page_last"] - df["page_count_full"] + 1

    # Set the actual page count for pruned articles that end on the same page
    # where the next article starts
    df["canonical_page_last"] = np.where(
        df.pruned == True, df.canonical_page_last + 1, df.canonical_page_last
    )

    return df


def set_tif_path(df, can_src_name, dir_tif):
    df["canonical_dir_tif"] = (
        dir_tif
        + "/"
        + can_src_name
        + "/"
        + df[["year", "month", "day"]].astype(str).apply(lambda x: "/".join(x), axis=1)
        + "/a"
    )

    df["canonical_fname_tif"] = (
        can_src_name
        + "-"
        + df[["year", "month", "day"]].astype(str).apply(lambda x: "-".join(x), axis=1)
        + "-a-p"
        + df["canonical_page_first"].map(lambda x: "{:04d}".format(x))
        + ".tif"
    )

    df["canonical_path_tif"] = df["canonical_dir_tif"] + "/" + df["canonical_fname_tif"]

    return df


def main():

    args = parse_args()

    df = pd.read_csv(args.f_in, sep="\t", parse_dates=["issue_date"])
    can_src_name = args.f_in.split(".")[0].split("-")[-1]  # e.g. FedGazDe

    df.sort_values(by=["issue_date", "article_page_first", "article_docid"], inplace=True)
    # deduplication on unique article id
    df["is_duplicate"] = df["article_docid"].duplicated()
    df = df.loc[df["is_duplicate"] == False]

    df = df.reset_index(drop=True)

    # parse date
    df["year"] = df["issue_date"].map(lambda x: x.year)
    df["month"] = df["issue_date"].map(lambda x: x.strftime("%m"))
    df["day"] = df["issue_date"].map(lambda x: x.strftime("%d"))

    df["edition"] = "a"

    # set attribute whether pdf is a scan with OCR or a fully digital copy
    df["ocr"] = np.where(df["issue_date"] <= "1999-06-15", True, False)

    df = set_empirical_page_count(df, can_src_name, args.dir_pdf, args.f_pages)

    df = find_overlapping_pages(df)
    df = set_canonical_numbering(df)
    df = set_tif_path(df, can_src_name, args.dir_tif)

    df.to_csv(args.f_out, sep="\t", index=False)


################################################################################
if __name__ == "__main__":
    main()
