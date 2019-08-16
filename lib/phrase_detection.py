#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Extract phrases with Gensim
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
from gensim.models.word2vec import LineSentence
from gensim.models.phrases import Phrases, Phraser


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
        "-t",
        "--threshold",
        required=False,
        action="store",
        dest="thres",
        default=0.85,
        help="threshold for the scoring function",
    )

    parser.add_argument(
        "-l",
        "--language",
        required=True,
        action="store",
        dest="lang",
        help="provide language in order to set stop words",
    )

    parser.add_argument(
        "-min",
        "--minimum",
        required=False,
        action="store",
        dest="min",
        default=100,
        help="minimum number of occurrences to be considered as ngram",
    )

    parser.add_argument(
        "--trigram",
        required=False,
        action="store",
        dest="trigram",
        help="extracting trigrams in addition to bigrams",
    )

    return parser.parse_args()


def write_ngrams(filename, ngrams):
    """
    Write ngrams into tsv file sorted by descendings score
    """
    with open(filename, mode="w") as f_out:
        sorted_ngrams = sorted(ngrams.items(), key=lambda kv: kv[1][1], reverse=True)
        for ngram, score in sorted_ngrams:
            ngram = "_".join([x.decode("utf8") for x in ngram])
            line = "{}\t{}\n".format(ngram, score)
            f_out.write(line)


def main():

    args = parse_args()

    if args.lang == "de":
        stopwords = ""
    elif args.lang == "fr":
        stopwords = ("de", "du", "de la", "de l'")
    else:
        stopwords = ""

    phrases_bigram = Phrases(
        LineSentence(args.f_in),
        min_count=args.min,
        threshold=args.thres,
        scoring="npmi",
        common_terms=stopwords,
    )

    bigram = Phraser(phrases_bigram)
    bigrams = bigram.phrasegrams

    f_out = args.f_out + "_bigrams.txt"
    write_ngrams(f_out, bigrams)

    if args.trigram:
        phrases_trigram = Phrases(
            phrases_bigram[LineSentence(args.f_in)],
            min_count=args.min,
            threshold=args.thres,
            scoring="npmi",
            common_terms=stopwords,
        )
        trigrams = trigram.phrasegrams
        trigram = Phraser(phrases_trigram)

        f_out = args.f_out + "_trigrams.txt"
        write_ngrams(f_out, trigrams)


################################################################################
if __name__ == "__main__":
    main()
