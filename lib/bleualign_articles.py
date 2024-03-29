#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Chantal Amrhein <chantal.amrhein@uzh.ch>"

################################################################################
# Bleualign for articles is a tool based on the existing Bleualign tool for
# sentences (by Dr. Rico Sennrich). It is designed to align parallel articles
# (meaning a text and its direct translation) and identify comparable articles
# (meaning two non-parallel texts - often in different languages -
# about the same topic).
#
# The script takes multiple file pairs (split in articles) in a source and
# target language, as well as a translated version of the source text
# in the target language.
#
# For each file pair, a new thread is started that uses dynamic programming to
# maximise the BLEU score over all found article alignments. Since some pairs
# should not be aligned but still contribute (minimally )to the overall BLEU
# score, all pairs returned by the dynamic programming approach are evaluated
# again.
#
# If the BLEU score is above a certain threshold, the pair is accepted as
# parallel articles. Else, a combination of the similarity in length and the
# matching numbers in the articles decides whether the articles should still be
# considered parallel articles. As a last step (if the pair is not decided to
# be parallel), the script checks whether they could be comparable articles
# using a tf/idf vectorizer.
################################################################################

# imported modules
from score import *
import argparse
import random
import re
from collections import defaultdict
import os.path
from lxml import etree
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import csv

# global variables
# parsing xml with utf-8 encoding and removing blank text
parser = etree.XMLParser(remove_blank_text=True, encoding="utf-8")


################################################################################


def parse_args():
    """parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    # required arguments: a source file, the source file translated into the target language, a target file
    # optional arguments: name for output file, whether or not comparable articles should be included in alignments-file or stored separatly
    parser.add_argument(
        "-src", "--source", required=True, action="store", dest="src", help="source text",
    )
    parser.add_argument(
        "-trg", "--target", required=True, action="store", dest="trg", help="target text",
    )
    parser.add_argument(
        "-t", "--translation", required=True, action="store", dest="t", help="source translation",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default="alignments.xml",
        action="store",
        dest="output",
        help="alignment output file name",
    )
    parser.add_argument(
        "-c", "--comparable", required=False, default=False, action="store_true", dest="comp",
    )

    return parser.parse_args()


################################################################################


def read_file(filename):
    """reads a given file into a string"""

    with open(filename, mode="r", encoding="utf-8") as infile:
        return infile.read()


################################################################################


def split_articles(text, string):
    """splits a given string into articles"""

    return [article for article in text.split(string) if article != "\n" and article != " \n"]


################################################################################


def split_sentences(articles):
    """splits all articles into sentences"""

    return [article.lstrip().rstrip().split("\n") for article in articles]


################################################################################


def num_repr(sentences):
    """extracts a list of numbers from a list of sentences in order of appearance"""

    return [
        re.sub(r"[,\.]", "", word)
        for sentence in sentences
        for word in sentence.split()
        if word.isnumeric() or re.match(r"\d+[,\.]\d+", word)
    ]


################################################################################


def write_alignments_to_xml(alignments, outfile):
    """uses the computed alignments to generate an article alignment xml"""

    root = etree.Element("TEI")
    xml = etree.ElementTree(root)

    if not alignments:
        xml.write(outfile, xml_declaration=True, encoding="utf-8", pretty_print=True)
        print("No alignments found.")
        return None

    header = etree.SubElement(root, "teiHeader")
    try:
        header.text = alignments[0]["src"][:14]  # extract path to language folder
    except IndexError:
        header.text = "LANGUAGEFOLDER"

    linkGrp = etree.SubElement(root, "linkGrp")
    try:
        src_lang = re.search("[_./](..)[_./]", alignments[0]["src"]).group(1)
        trg_lang = re.search("[_./](..)[_./]", alignments[0]["trg"]).group(1)
    except (AttributeError, IndexError):
        src_lang = "X"
        trg_lang = "X"
    linkGrp.set("lang", src_lang + ";" + trg_lang)
    linkGrp.set("targType", "yearbook")
    linkGrp.set("xtargets", alignments[0]["src"] + ";" + alignments[0]["trg"])

    for aligned in alignments:
        article = etree.SubElement(linkGrp, "link")
        article.set("targType", "article")
        article.set("method", aligned.get("method"))
        article.set("bleu", f'{aligned.get("bleu"):.2f}')
        article.set("overlap_numbers", f'{aligned.get("overlap_numbers"):.2f}')
        article.set("cosine_similarity", f'{aligned.get("cosine_similarity", 0):.2f}')
        article.set("xtargets", aligned["src"] + ";" + aligned["trg"])

    xml.write(outfile, xml_declaration=True, encoding="utf-8", pretty_print=True)


################################################################################


def merge_cells(current, left, i, j, raw_score):
    """merge function for dynamic programming - isolated for testing"""

    # iterate over all alignments stored in left cell
    for art, alignment in sorted(left[1].items(), reverse=True):

        # if both alignments are the same or left cell has no alignment -> skip
        if alignment == current[1][art]:
            pass
        elif alignment[0] is None:
            pass

        # exchange alignments of current cell for ones from left cell
        else:
            # only do this if BLEU score for alignment in left cell is higher
            if current[1][art] == () or alignment[1] > current[1][art][1]:
                # if new target article was already part of an alignment in current cell:
                if alignment[0] in current[2]:
                    keep = current[2][alignment[0]]
                    # check whether new alignment is still better than the one with the used target article
                    if current[1][keep] == () or current[1][keep][1] < alignment[1]:
                        # if yes delete previous alignment with target article in current cell
                        # and add new alignment from left
                        try:
                            del current[2][current[1][art][0]]
                        except IndexError:
                            pass

                        del current[1][keep]
                        current[1][art] = alignment
                        current[2][alignment[0]] = art
                    else:
                        del current[1][art]
                # if new target article not in alignments of current cell, add new alignment
                else:
                    try:
                        del current[2][current[1][art][0]]
                    except IndexError:
                        pass

                    current[1][art] = alignment
                    current[2][alignment[0]] = art

    # calculate overall BLEU score of current cell
    current[0] = sum([two for one, two in current[1].values()])

    return current


################################################################################


def compute_max_alignment(trans_data, trg_data):
    """maximises BLEU score using dynamic programming techniques and returns aligned articles"""

    #  set up matrix for dynmic programming
    # each matrix cell looks like this:
    # [overall BLEU score for this cell,
    #   {source article index : (target article index, BLEU score for this article pair), ...}
    #   {target article index : source article index, ...} --> for easy access to occupied target indices
    #  ]

    n_docs_trans = len(trans_data)
    n_docs_trg = len(trg_data)

    matrix = [
        [[0.0, defaultdict(tuple), defaultdict(int)] for art2 in range(0, n_docs_trg + 1)]
        for art in range(0, n_docs_trans + 1)
    ]

    # iterate over each cell (i,j)
    for i, article1 in enumerate(trans_data):
        for j, article2 in enumerate(trg_data):

            #### settings for current matrix move ####

            # define important cells used for dynamic programming:

            above = matrix[i][j + 1]  # cell vertically above of current
            left = matrix[i + 1][j]  # cell horizontally to the left of current
            diag = matrix[i][j]  # cell diagonally before current
            current = matrix[i + 1][j + 1]  # current cell

            # Only compute BLEU score when the texts are similar in length
            # (number of tokens). Otherwise, an arbitrary low score is defined
            # to speed up the alignment process
            art1_length = sum([len(sent.split()) for sent in article1])
            art2_length = sum([len(sent.split()) for sent in article2])
            ratio_length = min((art1_length, art2_length)) / max((art1_length, art2_length))

            if ratio_length > 0.6:
                # compute BLEU score between current translated source and target article:
                refs = cook_refs([" ".join(article2).split()[1:]])
                test = cook_test(" ".join(article1).split()[1:], refs)
                raw_score = score_cooked([test])
            else:
                raw_score = 0.001

            # score if alignment of current cell is used (raw_score + score of diagonal cell before)
            score = diag[0] + raw_score

            #### 4 possible moves to go forward in the matrix ####

            #  1. possible move - merge cell from above and left
            # (if their scores are higher or equal than current score and not the same as the score from diagonal cell before)
            # this is not a dynamic programming move as we have to compare all alignments from the two cells
            # however it is necessary to be able to merge cells if alignment pairs are overcrossing !

            if (above[0] >= score and left[0] >= score) and (
                above[0] != diag[0] and left[0] != diag[0]
            ):

                # copy content from cell above to current cell
                current[1] = above[1].copy()
                current[2] = above[2].copy()

                # do the merging
                merge_cells(current, left, i, j, raw_score)

            #  2. possible move - take cell from above
            # (if its score is higher than left cell and  diagonal cell + raw_score)
            elif above[0] >= score and above[0] >= left[0]:
                current[0] = above[0]
                current[1] = above[1].copy()
                current[2] = above[2].copy()

            # 3. possible move - take cell from left
            # (if its score is higher than diagonal cell + raw_score)
            elif left[0] >= score:
                current[0] = left[0]
                current[1] = left[1].copy()
                current[2] = left[2].copy()

            # 4. possible move - add current alignment to alignments from diagonal cell
            else:
                current[0] = score
                current[1] = diag[1].copy()
                current[1][i] = (j, raw_score)
                current[2] = diag[2].copy()
                current[2][j] = i

    # return the resulting alignments with their BLEU scores
    return matrix[-1][-1][1]


################################################################################


def align(src_articles, trg_articles, trans_articles):
    "performs article alignment for a magazine and its translation"

    # split all articles to sentences
    src_data = split_sentences(src_articles)
    trg_data = split_sentences(trg_articles)
    trans_data = split_sentences(trans_articles)

    # get the tfidf matrix in order to find comparable articles later
    tfidf = TfidfVectorizer().fit_transform(trans_articles + trg_articles)

    #  for dynamic programming to find all alignments exchange trans_data and trg_data if the latter is larger than the former
    if len(trans_data) > len(trg_data):
        alignments = compute_max_alignment(trg_data, trans_data)
        swapped = True
    else:
        alignments = compute_max_alignment(trans_data, trg_data)
        swapped = False

    # set up dictionaries for parallel articles and comparable articles
    definitive_alignments = []
    comparable_alignments = []

    # iterate over all possible alignments found with dynamic programming
    for art, data in alignments.items():

        # get the ids of the src and trg articles for each pair
        # if trans_data and trg_data were exchanged find the correct ids!
        try:
            if swapped:
                bleu = data[1]
                src_art = src_data[data[0]]
                trg_art = trg_data[art]
            else:
                bleu = data[1]
                src_art = src_data[art]
                trg_art = trg_data[data[0]]
        except (TypeError, IndexError):
            continue

        # get a set of numbers occurring in each article, compute how many percent are represented in both articles
        # If there are only few numbers, set arbitrary score as it is not reliable
        src_nums = set(num_repr(src_art))
        trg_nums = set(num_repr(trg_art))

        if max(len(src_nums), len(trg_nums)) > 3:
            sim_nums = len(src_nums & trg_nums) / max(len(src_nums), len(trg_nums))
        else:
            sim_nums = 0.4

        # if the BLEU score > 0.1 and overlapping numbers > 0.5 accept as parallel articles
        if bleu > 0.1 and sim_nums >= 0.4:

            align_info = {
                "src": src_art[0],
                "trg": trg_art[0],
                "method": "BLEU",
                "bleu": bleu,
                "overlap_numbers": sim_nums,
            }
            definitive_alignments.append(align_info)

        # else check how many numbers are identical
        # weighted by the difference in length of the articles (measured with characters)
        else:
            # get number of characters in each article, compute percentual difference of article lengths
            len_src = sum([len(sent) for sent in src_art[1:]])
            len_trg = sum([len(sent) for sent in trg_art[1:]])
            sim_len = min(len_src, len_trg) / max(len_src, len_trg)

            # combine the two measures to a weighted score
            weighted_sim = (0.2 * sim_len) + (0.8 * sim_nums)

            # if this score is higher than 0.55 also accept them as parallel articles
            if weighted_sim > 0.55:
                align_info = {
                    "src": src_art[0],
                    "trg": trg_art[0],
                    "method": "number_length_matching",
                    "bleu": bleu,
                    "overlap_numbers": sim_nums,
                    "number_length_score": weighted_sim,
                }
                definitive_alignments.append(align_info)

            # else compute how similar the articles are using the tf/idf vectorizer
            else:
                try:
                    cos_sim_tfidf = float(
                        linear_kernel(
                            tfidf[src_data.index(src_art)],
                            tfidf[len(src_data) + trg_data.index(trg_art)],
                        )
                    )

                    # if this score is higher than 0.5 accept them as comparable articles
                    if cos_sim_tfidf > 0.5:
                        align_info = {
                            "src": src_art[0],
                            "trg": trg_art[0],
                            "method": "tfidf",
                            "bleu": bleu,
                            "overlap_numbers": sim_nums,
                            "cosine_similarity": cos_sim_tfidf,
                        }
                        comparable_alignments.append(align_info)
                except IndexError:
                    print("TODO: fix the tf-idf alignment")

    return definitive_alignments, comparable_alignments


def corpus_figures(articles, resource, prefix):

    meta = {}

    meta[prefix] = resource

    # add corpus figures
    meta[prefix + "_n_docs"] = len(articles)
    content = " ".join(articles)
    meta[prefix + "_n_chars"] = len(content)
    meta[prefix + "_n_tokens"] = len(content.split())
    n_sents = sum([len(split_articles(art, "\n")) for art in articles])
    meta[prefix + "_n_sentences"] = n_sents

    return meta


def alignment_stats(src_articles, trg_articles, definitive_alignments, comparable_alignments):

    meta = {}

    # compute how many parallel and how many comparable article pairs were found
    meta["dp_parallel_pairs"] = len(definitive_alignments)
    meta["potential_pairs"] = len(comparable_alignments)

    meta["src_rel_aligned"] = round(len(definitive_alignments) / len(src_articles), 2)
    meta["trg_rel_aligned"] = round(len(definitive_alignments) / len(trg_articles), 2)

    meta["ratio_src_trg"] = round(len(src_articles) / len(trg_articles), 2)

    meta["src_unaligned"] = (
        len(src_articles) - len(definitive_alignments) - len(comparable_alignments)
    )
    meta["trg_unaligned"] = (
        len(trg_articles) - len(definitive_alignments) - len(comparable_alignments)
    )

    return meta


def filter_multi_alignments(alignments):
    """
    Keep only the best alignments if an article is aligned multiple times due to batching
    """

    bad_aligns = set()

    for idx_a, align_a in enumerate(alignments):
        best_align = idx_a
        for idx_b, align_b in enumerate(alignments):
            if idx_a == idx_b:
                continue

            # duplicate criterion on target side
            if align_a["trg"] == align_b["trg"]:
                if alignments[best_align]["bleu"] >= align_b["bleu"]:
                    bad_aligns.add(idx_b)
                else:
                    bad_aligns.add(best_align)  # discard current best
                    best_align = idx_b  # set new best alignment

    print(f"Remove {len(bad_aligns)} duplicated alignments from a total of {len(alignments)}:")
    for idx in bad_aligns:
        print("\t", alignments[idx])

    filtered = [align for idx, align in enumerate(alignments) if idx not in bad_aligns]

    return filtered


def batch_align(src_articles, trg_articles, trans_articles, batch_size_src=500):
    """
    Start batch-wise alignment process to avoid memory issues
    """

    definitive_alignments = []
    comparable_alignments = []

    # ratio_src_trg = len(src_articles) / len(trg_articles)

    for i, start_src in enumerate(range(0, len(src_articles), batch_size_src)):
        end_src = min(start_src + batch_size_src, len(src_articles))

        # TODO
        # Doing a full search across all documents is too slow.
        # Instead, search within an overlapping interval.
        # The interval is scaled, assuming an equal distribution within a year,
        # and increases during the process to account for irregularities in the distribution.
        # start_trg = max(0, int(start_src / ratio_src_trg - start_src * 0.2))
        # end_trg = min(len(trg_articles), int(end_src / ratio_src_trg + end_src * 0.2))
        start_trg = 0
        end_trg = len(trg_articles)
        print("\tBATCH:", i)
        print(
            f"\tCompute source alignments for document range between {start_src} and {end_src} of total {len(src_articles)}"
        )
        print(
            f"\tCompute target alignments for document range between {start_trg} and {end_trg} of total {len(trg_articles)}"
        )
        print("\t", "_" * 20)

        definitive_alignments_temp, comparable_alignments_temp = align(
            src_articles[start_src:end_src], trg_articles, trans_articles[start_src:end_src],
        )

        # aggregate across batches
        definitive_alignments += definitive_alignments_temp
        comparable_alignments += comparable_alignments_temp

    return definitive_alignments, comparable_alignments


################################################################################


def main():
    """main function to handle document aligning with BLEU"""

    # parse arguments
    args = parse_args()

    print(
        f"""\n------------------------------------------------------------------
        Starting alignment process...
        Name of source file: {args.src}
        Name of target file: {args.trg}
        """
    )

    # read all files
    src = read_file(args.src)
    trg = read_file(args.trg)
    trans = read_file(args.t)

    # remove first and last line of file since there is no volume organization
    src = src[src.find("\n") + 1 : src.rfind(".EOB") - 5]
    trg = trg[trg.find("\n") + 1 : trg.rfind(".EOB") - 5]
    trans = trans[trans.find("\n") + 1 : trans.rfind(".EOB") - 5]

    # split the magazine into articles
    src_articles = split_articles(src, ".EOA")
    trg_articles = split_articles(trg, ".EOA")
    trans_articles = split_articles(trans, ".EOA")

    definitive_alignments, comparable_alignments = batch_align(
        src_articles, trg_articles, trans_articles
    )
    definitive_alignments = filter_multi_alignments(definitive_alignments)
    comparable_alignments = filter_multi_alignments(comparable_alignments)

    # write alignments into xml files that optionally includes
    # heuristically similar alignments
    if args.comp:
        definitive_alignments += comparable_alignments
        write_alignments_to_xml(definitive_alignments, args.output)
    else:
        write_alignments_to_xml(definitive_alignments, args.output)
        fname = args.output.replace(".xml", "_comparable.xml")
        write_alignments_to_xml(comparable_alignments, fname)

    # prepare all statistics
    align_stats = alignment_stats(
        src_articles, trg_articles, definitive_alignments, comparable_alignments
    )
    src_stats = corpus_figures(src_articles, args.src, "src")
    trg_stats = corpus_figures(trg_articles, args.trg, "trg")

    stats = {**align_stats, **src_stats, **trg_stats}

    # write alignment statistics to tsv
    fname_stats = args.output[:-4] + "_stats.tsv"
    with open(fname_stats, "w", newline="") as csvfile:
        fieldnames = sorted(stats.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerow(stats)


################################################################################

if __name__ == "__main__":

    main()
