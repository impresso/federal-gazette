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
import numpy as np
from collections import Counter


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

    return parser.parse_args()


def set_page_count(df, lang):
    df_pages = pd.read_csv(lang + ".pages.tsv", sep="\t", header=None)
    df_pages = df_pages.rename(columns={0: "pdf_path", 1: "page_count"})

    # derive file path
    df["pdf_path"] = (
        "data_pdf/"
        + lang
        + "/"
        + df["issue_date"].map(lambda x: str(x.year))
        + "/"
        + df["issue_date"].map(lambda x: str(x.date()))
        + "/"
        + df["article_docid"].map(lambda x: str(x))
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

    for year in df.year.unique():
        year_issues = df.loc[df.year == year, "issue_number"].unique()

        counter = Counter()

        for volume in df[df.year == year].volume_number.unique():

            year_vol_arts = [
                index
                for index, row in df[
                    (df.year == year) & (df.volume_number == volume)
                ].iterrows()
            ]

            titles = ["inserate", "beilage"]

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
                # issue_number = df.loc[art, 'issue_number']
                # issue_number_sub = df.loc[art + 1, 'issue_number']

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
                        if art_length >= 1:
                            # if an article ends shares its last page with the subsequent article
                            # set article's last page based on its page count deducted by 1 to prune it at the last full page
                            # this is used a heuristic until there is a proper segmentation
                            df.loc[art, "article_page_last"] = (
                                df.loc[art, "article_page_first"] + art_length - 1
                            )  # before: subtraction by 2
                            counter["segment_in"] += 1
                            df.loc[art, "log"] = "segment_in more_than_one_page"

                        else:
                            # additionally, article starts and ends on the same page
                            df.loc[art, "article_page_last"] = (
                                df.loc[art, "article_page_first"] + art_length - 1
                            )
                            counter["segment_in"] += 1
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
    Maybe less than page_count since only entirely used pages are counted.
    The remainder is assigned to the subsequent article
    """
    # set default value
    df["page_count_full"] = df["page_count"]

    for i, row in df.iterrows():
        try:
            if df.loc[i, "article_page_last"] == df.loc[i + 1, "article_page_first"]:
                df.loc[i, "page_count_full"] -= 1
        except KeyError:
            # there is no subsequent article for the final article
            continue

    return df


def set_impresso_numbering(df):
    df["impresso_issue_page"] = df.groupby(["issue_date"])["page_count"].apply(
        lambda x: x.cumsum()
    )
    df["impresso_issue_page"] = df["impresso_issue_page"] - df["page_count"] + 1

    df["impresso_issue_page"] = df["impresso_issue_page"].astype("int")

    # set the 4-digit format
    df["impresso_issue_page"] = df["impresso_issue_page"].map(
        lambda x: "{:04d}".format(x)
    )

    return df


def set_tif_path(df, lang):
    abbr = "FedGaz" + lang.capitalize()
    df["canonical_dir_tif"] = (
        "data_tif/"
        + abbr
        + "/"
        + df[["year", "month", "day"]].astype(str).apply(lambda x: "/".join(x), axis=1)
        + "/a"
    )

    df["canonical_fname_tif"] = (
        abbr
        + "-"
        + df[["year", "month", "day"]].astype(str).apply(lambda x: "-".join(x), axis=1)
        + "-a-"
        + df["impresso_issue_page"].map(str)
        + ".tif"
    )

    df["canonical_path_tif"] = df["canonical_dir_tif"] + "/" + df["canonical_fname_tif"]

    return df


def main():

    args = parse_args()
    f_in = args.f_in
    f_out = args.f_out

    df = pd.read_csv(f_in, sep="\t", parse_dates=["issue_date"])
    lang = f_in.split(".")[0].split("-")[-1]  # parse language id

    df.sort_values(
        by=["issue_date", "article_page_first", "article_docid"], inplace=True
    )
    df = df.reset_index(drop=True)

    # parse date
    df["year"] = df["issue_date"].map(lambda x: x.year)
    df["month"] = df["issue_date"].map(lambda x: x.strftime("%m"))
    df["day"] = df["issue_date"].map(lambda x: x.strftime("%d"))

    df["edition"] = "a"

    df = set_page_count(df, lang)
    df = set_continious_page_numbering(df)
    df = set_page_count_full(df)
    df = set_impresso_numbering(df)
    df = set_tif_path(df, lang)

    df.to_csv(f_out, sep="\t", index=False)


################################################################################
if __name__ == "__main__":
    main()
