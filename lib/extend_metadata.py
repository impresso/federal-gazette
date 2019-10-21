#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Extend tsv-file with more metadata (path to pdf, number of pdf pages)
Sorry, for the awful code which seems necessary to cover various cases
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"

from collections import Counter
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
        "-o",
        "--output",
        required=True,
        action="store",
        dest="f_out",
        help="output file",
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

    return parser.parse_args()


def set_page_count(df, can_src_name, dir_pdf):
    df_pages = pd.read_csv(can_src_name + ".pages.tsv", sep="\t", header=None)
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
    # reason: last page contains only meta-information in this case,.
    df.loc[df["issue_date"] <= "1999-06-15", "page_count"] = df.loc[
        df["issue_date"] <= "1999-06-15", "page_count"
    ].map(lambda x: x - 1)

    return df


def set_continious_page_numbering(df, print_log=False):

    df["log"] = ""
    df["article_page_last"] = np.nan
    df["pruned"] = False

    titles = ["inserate", "beilage"]

    for year in df.year.unique():

        counter = Counter()

        for volume in df[df.year == year].volume_number.unique():

            year_vol_arts = [
                index
                for index, row in df[
                    (df.year == year) & (df.volume_number == volume)
                ].iterrows()
            ]

            for art in year_vol_arts:
                art_start = df.loc[art, "article_page_first"]
                art_length = df.loc[art, "page_count"]
                try:
                    art_sub_start = df.loc[art + 1, "article_page_first"]
                except KeyError:
                    # for the last article there is no subsequent article
                    # set hypothetical start of next article
                    art_sub_start = art_start + art_length

                issue_end = df.loc[art, "issue_page_last"]

                if art_sub_start == art_start + art_length:
                    # if an article ends at the end of a page
                    # set article's last page based on its page count
                    df.loc[art, "article_page_last"] = (
                        df.loc[art, "article_page_first"] + art_length - 1
                    )
                    counter["segment_end"] += 1
                    df.loc[art, "log"] = "segment_end_1"

                elif art_sub_start == art_start + art_length - 1 == issue_end:
                    # handle special case for last article before supplements
                    # set article's last page based on its page count
                    df.loc[art, "article_page_last"] = (
                        df.loc[art, "article_page_first"] + art_length - 1
                    )
                    counter["segment_end"] += 1
                    df.loc[art, "log"] = "segment_end_2"

                elif art_sub_start == 1:
                    # if article is at the end of the volume (before 1999) or at the end of year (since 1999)
                    # set article's last page based on its page count
                    df.loc[art, "article_page_last"] = (
                        df.loc[art, "article_page_first"] + art_length - 1
                    )
                    counter["segment_end"] += 1
                    df.loc[art, "log"] = "segment_end_3"

                # irregular cases for supplements or in-page segementation
                else:
                    if art_start == issue_end or any(
                        t in df.loc[art, "article_title"].lower() for t in titles
                    ):
                        # if it is supplement that are defined as a one pager at the end OR based on title
                        # set article's first page one higher wtr to the end of the preceding article
                        df.loc[art, "article_page_first"] = (
                            df.loc[art - 1, "article_page_last"] + 1
                        )
                        # and adjust article's last page accordingly based on page count
                        df.loc[art, "article_page_last"] = (
                            df.loc[art, "article_page_first"] + art_length - 1
                        )
                        counter["supplements"] += 1
                        df.loc[art, "log"] = "supplements"

                    elif art_sub_start == art_start + art_length - 1 != issue_end:
                        # if an article shares its last page with the subsequent article
                        # set article's last page based on its page count deducted by 1 to prune it at the last full page
                        # this is used heuristically before we apply logical article segmentation

                        df.loc[art, "pruned"] = True
                        df.loc[art, "article_page_last"] = (
                            df.loc[art, "article_page_first"] + art_length - 1
                        )
                        counter["segment_in"] += 1

                        if art_length >= 1:
                            df.loc[art, "log"] = "segment_in more_than_one_page"

                        else:
                            # article starts and ends on the same page
                            df.loc[art, "log"] = "segment_in less_than_one_page"

                    else:
                        if print_log:
                            print(
                                art,
                                df.loc[art, "article_title"],
                                df.loc[art, "article_pdf_url"],
                                art_sub_start,
                                art_start,
                                art_length,
                            )
                        # set proper empirical page count even when there are some irregularities in this record
                        df.loc[art, "article_page_last"] = (
                            df.loc[art, "article_page_first"] + art_length - 1
                        )
                        counter["segment_error"] += 1
                        df.loc[art, "log"] = "segment_suspicious"
        if print_log:
            print("\n")
            print(year)
            print("# articles end-page segmentation:", counter["segment_end"])
            print("# articles in-page segmentation:", counter["segment_in"])
            print("# supplements (no segmentation):", counter["supplements"])
            print("# articles suspicious segmentation:", counter["segment_error"])
            total_art = sum([val for key, val in counter.items()])
            print("# articles (total):", total_art)

    df["article_page_last"] = df["article_page_last"].astype("int")

    return df


def set_page_count_full(df):
    """
    The number may be one less than page_count since only pages
    which belong exclusively to an article are counted.
    The potential remainder is assigned to the subsequent article.
    """

    df["article_page_first_next"] = df["article_page_first"].shift(-1)
    df["issue_date_next"] = df["issue_date"].shift(-1)
    df["page_count_full"] = np.where(
        (df.article_page_last == df.article_page_first_next)
        & (df.issue_date == df.issue_date_next),
        df.page_count - 1,
        df.page_count,
    )

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

    # Set actual page count for pruned articles that end on the same page
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

    df.sort_values(
        by=["issue_date", "article_page_first", "article_docid"], inplace=True
    )
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

    df = set_page_count(df, can_src_name, args.dir_pdf)
    df = set_continious_page_numbering(df)
    df = set_page_count_full(df)
    df = set_canonical_numbering(df)
    df = set_tif_path(df, can_src_name, args.dir_tif)

    df.to_csv(args.f_out, sep="\t", index=False)


################################################################################
if __name__ == "__main__":
    main()
