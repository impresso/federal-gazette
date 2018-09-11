#!/usr/bin/env python2
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
import codecs
import random
import re
from collections import defaultdict
import os.path
from lxml import etree
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from multiprocessing import Queue, Process

# global variables
# parsing xml with utf-8 encoding and removing blank text
parser = etree.XMLParser(remove_blank_text=True, encoding="utf-8")

################################################################################


def parse_args():
    """parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    # required arguments: a source file, the source file translated into the target language, a target file
    # optional arguments: name for output file, whether or not comparable articles should be included in alignments-file or stored separatly
    parser.add_argument("-src", "--source",  required=True,
                        action="store", dest="src", help="source text")
    parser.add_argument("-trg", "--target",  required=True,
                        action="store", dest="trg", help="target text")
    parser.add_argument("-t", "--translation",  required=True,
                        action="store", dest="t", help="source translation")
    parser.add_argument("-o", "--output", required=False, default="alignments.xml",
                        action="store", dest="output", help="alignment output file name")
    parser.add_argument("-c", "--comparable", required=False,
                        default=False, action="store_true", dest="comp")

    return parser.parse_args()

################################################################################


def read_file(filename):
    """reads a given file into a string"""

    with codecs.open(filename, 'r', 'utf-8') as infile:
        return infile.read()

################################################################################


def split_articles(text, string):
    """splits a given string into articles"""

    return [article for article in text.split(string) if article != u"\n" and article != u" \n"]

################################################################################


def split_sentences(articles):
    """splits all articles into sentences"""

    return [article.lstrip().rstrip().split('\n') for article in articles]

################################################################################


def num_repr(sentences):
    """extracts a list of numbers from a list of sentences in order of appearance"""

    return [re.sub('[,\.]', '', word) for sentence in sentences for word in sentence.split() if word.isnumeric() or re.match('\d+[,\.]\d+', word)]

################################################################################


def write_alignments_to_xml(alignments, src_name, trg_name, outfile):
    """uses the computed alignments to generate an article alignment xml"""

    if os.path.isfile(outfile):
        # open existing xml
        xml = etree.parse(outfile, parser)
        root = xml.getroot()

    else:
        # set up xml
        root = etree.Element('TEI')
        xml = etree.ElementTree(root)

    # create basic xml structure for new book
    header = etree.SubElement(root, "teiHeader")
    header.text = src_name[:-7]

    linkGrp = etree.SubElement(root, "linkGrp")
    linkGrp.set("lang", src_name[-6:-4]+";"+trg_name[-6:-4])
    linkGrp.set("targType", "yearbook")
    linkGrp.set("xtargets", src_name+";"+trg_name)

    # iterate over all articles
    for src_art, trg_art in alignments.items():

        # insert xml element for current article
        article = etree.SubElement(linkGrp, "link")
        article.set("targType", "article")
        article.set("xtargets", src_art+";"+trg_art)

    # write XML tree to file
    xml.write(outfile, xml_declaration=True,
              encoding='utf-8', pretty_print=True)

################################################################################


def merge_cells(current, left, i, j, raw_score):
    """merge function for dynamic programming - isolated for testing"""

    # iterate over all alignments stored in left cell
    for art, alignment in sorted(left[1].items(), reverse=True):

        # if both alignments are the same or left cell has no alignment -> skip
        if alignment == current[1][art]:
            pass
        elif alignment[0] == None:
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

    # set up matrix for dynmic programming
    # each matrix cell looks like this:
    # [overall BLEU score for this cell,
    #   {source article index : (target article index, BLEU score for these articles), ...}
    #   {target article index : source article index, ...} --> for easy access to occupied target indices
    # ]

    n_docs_trans = len(trans_data)
    n_docs_trg = len(trg_data)

    matrix = [[[0., defaultdict(tuple), defaultdict(int)] for art2 in range(
        0, n_docs_trg+1)] for art in range(0, n_docs_trans+1)]



    # iterate over each cell (i,j)
    for i, article1 in enumerate(trans_data):
        # Show progress
        if n_docs_trans % 20:
            print 'Compute BLEU alignment scores of document {} from {}.'.format(i, n_docs_trans)

        for j, article2 in enumerate(trg_data):

            #### settings for current matrix move ####

            # define important cells used for dynamic programming:

            above = matrix[i][j+1]  # cell vertically above of current
            left = matrix[i+1][j]  # cell horizontally to the left of current
            diag = matrix[i][j]  # cell diagonally before current
            current = matrix[i+1][j+1]  # current cell



            # Only compute BLEU score when the texts are similar in length
            # (number of tokens). Otherwise, an arbitrary low score is defined
            # to speed up the alignment process
            art1_length = sum([len(sent.split()) for sent in article1])
            art2_length = sum([len(sent.split()) for sent in article2])
            ratio_length = min((art1_length, art2_length)) / float(max((art1_length, art2_length)))

            if (ratio_length > 0.6 and ratio_length <= 1):
                # compute BLEU score between current translated source and target article:
                refs = cook_refs([' '.join(article2).split()[1:]])
                test = cook_test(' '.join(article1).split()[1:], refs)
                raw_score = score_cooked([test])
            else:
                raw_score = 0.001

            # score if alignment of current cell is used (raw_score + score of diagonal cell before)
            score = diag[0] + raw_score


            #### 4 possible moves to go forward in the matrix ####

            # 1. possible move - merge cell from above and left
            # (if their scores are higher or equal than current score and not the same as the score from diagonal cell before)
            # this is not a dynamic programming move as we have to compare all alignments from the two cells
            # however it is necessary to be able to merge cells if alignment pairs are overcrossing !

            if (above[0] >= score and left[0] >= score) and (above[0] != diag[0] and left[0] != diag[0]):

                # copy content from cell above to current cell
                current[1] = above[1].copy()
                current[2] = above[2].copy()

                # do the merging
                merge_cells(current, left, i, j, raw_score)

            # 2. possible move - take cell from above
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


def align(src_book, trg_book, trans_book, queue):
    "performs article alignment for a magazine and its translation"

    # split the magazine to articles
    src_raw = split_articles(src_book, ".EOA")
    trg_raw = split_articles(trg_book, ".EOA")
    trans_raw = split_articles(trans_book, ".EOA")

    # split all articles to sentences
    src_data = split_sentences(src_raw)
    trg_data = split_sentences(trg_raw)
    trans_data = split_sentences(trans_raw)

    # remove the file names at top of magazine text
    src_file = src_data[0].pop(0)
    trg_file = trg_data[0].pop(0)
    trans_data[0].pop(0)




    # get the tfidf matrix in order to find comparable articles later
    tfidf = TfidfVectorizer().fit_transform(trans_raw + trg_raw)

    # for dynamic programming to find all alignments exchange trans_data and trg_data if the latter is larger than the former
    if len(trans_data) > len(trg_data):
        alignments = compute_max_alignment(trg_data, trans_data)
        swapped = True
    else:
        alignments = compute_max_alignment(trans_data, trg_data)
        swapped = False

    # generate status message
    output_str = ""
    output_str += "\n\nProcessing:"
    output_str += "\n" + src_file
    output_str += "\n" + trg_file
    output_str += "\n\n------------------------------------------------------------------\n"

    # set up dictionaries for parallel articles and comparable articles
    definitive_alignments = {}
    comparable_alignments = {}

    # iterate over all possible alignments found with dynamic programming
    for art, data in alignments.items():

        # get the ids of the src and trg articles for each pair
        # if trans_data and trg_data were exchanged find the correct ids!
        try:
            if swapped:
                score = data[1]
                src_art = src_data[data[0]]
                trg_art = trg_data[art]
            else:
                score = data[1]
                src_art = src_data[art]
                trg_art = trg_data[data[0]]
        except TypeError, IndexError:
            continue

        # if the BLEU score is higher than 0.1 accept them as parallel articles
        if score > 0.1:
            output_str += '\n\tsrc art - \033[92m '+src_art[0] + \
                ' \taligned with\t '+trg_art[0]+' \033[0m\t- trg art'
            definitive_alignments[src_art[0]] = trg_art[0]

        # else check how many numbers are identical
        # weighted by the difference in length of the articles (measured with characters)
        else:

            # get a list of numbers occurring in each article, compute how many percent are represented in both articles
            src_nums = set(num_repr(src_art))
            trg_nums = set(num_repr(trg_art))
            try:
                sim_nums = len(src_nums & trg_nums) / \
                    float(max(len(src_nums), len(trg_nums)))
            except ZeroDivisionError:
                sim_nums = 0.3

            # get number of characters in each article, compute percentual difference of article lengths
            len_src = sum([len(sent) for sent in src_art[1:]])
            len_trg = sum([len(sent) for sent in trg_art[1:]])
            sim_len = min(len_src, len_trg) / float(max(len_src, len_trg))

            # combine the two measures to a weighted score
            weighted_sim = (0.2 * sim_len) + (0.8 * sim_nums)

            # if this score is higher than 0.55 also accept them as parallel articles
            if weighted_sim > 0.55:
                output_str += '\n\tsrc art - \033[92m '+src_art[0] + \
                    ' \taligned with\t '+trg_art[0]+' \033[0m\t- trg art'
                definitive_alignments[src_art[0]] = trg_art[0]

            # else compute how similar the articles are using the tf/idf vectorizer
            else:
                cosine_similarities = linear_kernel(
                    tfidf[src_data.index(src_art)], tfidf).flatten()
                sim_tfidf = cosine_similarities[len(
                    src_data)+trg_data.index(trg_art)]

                # if this score is higher than 0.5 accept them as comparable articles
                if sim_tfidf > 0.5:
                    output_str += '\n\tsrc art - \033[94m '+src_art[0] + \
                        ' \tsimilar to\t '+trg_art[0]+' \033[0m\t- trg art'
                    comparable_alignments[src_art[0]] = trg_art[0]

    # compute how many articles were left unaligned
    src_not_aligned = len(
        src_data) - len(definitive_alignments.keys()+comparable_alignments.keys())
    trg_not_aligned = len(
        trg_data) - len(definitive_alignments.values()+comparable_alignments.values())

    # compute how many articles in total
    src_len = len(src_data)
    trg_len = len(trg_data)

    # compute how many possible pairs were found with dynamic programming
    dynamic_programming_output = len(alignments)

    # compute how many parallel and how many comparable article pairs were found
    found_parallel = len(definitive_alignments)
    found_comparable = len(comparable_alignments)

    # compute percents for statistics
    aligned_percent = int(float(found_parallel)/dynamic_programming_output*100)
    comparable_percent = int(float(found_comparable) /
                             dynamic_programming_output*100)
    src_percent = int(float(src_not_aligned)/src_len*100)
    trg_percent = int(float(trg_not_aligned)/trg_len*100)

    # add statistics to status message
    output_str += "\n\n------------------------------------------------------------------"
    output_str += "\n\nPossible alignment pairs found with dynamic progamming: {0:d}".format(
        dynamic_programming_output)
    output_str += "\n\033[92mFound {0:d} parallel articles\033[0m\t\t= {1:d}%".format(
        found_parallel, aligned_percent)
    output_str += "\n\033[94mFound {0:d} comparable articles\033[0m\t\t= {1:d}%".format(
        found_comparable, comparable_percent)

    output_str += "\n\nTotal source articles: {0:d}, total target articles: {1:d}".format(
        src_len, trg_len)
    output_str += "\n\033[93m{0:d} source articles left unaligned\033[0m\t= {1:d}%".format(
        src_not_aligned, src_percent)
    output_str += "\n\033[93m{0:d} target articles left unaligned\033[0m\t= {1:d}%\n".format(
        trg_not_aligned, trg_percent)
    output_str += "\n------------------------------------------------------------------"

    # put status message and alignment information on the queue
    queue.put(output_str)
    queue.put(src_file)
    queue.put(trg_file)
    queue.put(definitive_alignments)
    queue.put(comparable_alignments)

################################################################################


def main():
    """main function to handle document aligning with BLEU"""

    # parse arguments
    args = parse_args()

    # read all files
    src = read_file(args.src)
    trg = read_file(args.trg)
    translation = read_file(args.t)

    # split to books, articles and to sentences
    src_books = split_articles(src, ".EOB")
    trg_books = split_articles(trg, ".EOB")
    trans_books = split_articles(translation, ".EOB")

    print "\n------------------------------------------------------------------"
    print "------------------------------------------------------------------"
    print "\t\tStarting threads for {0:d} text collection(s)".format(len(src_books))
    print "------------------------------------------------------------------"
    print "------------------------------------------------------------------"

    # set up a list of all threads and a queue to store data
    threads = []
    queue = Queue()

    # iterate over each magazine pair
    for index, src_book in enumerate(src_books):

        trg_book = trg_books[index]
        trans_book = trans_books[index]

        # start a new thread to align articles of this magazine pair
        p = Process(target=align, args=(
            src_book, trg_book, trans_book, queue,))
        p.start()
        threads.append(p)

    # for each finished thread
    for t in threads:

        t.join()

        # print the status message
        print queue.get()

        # get the alignment information
        src_file = queue.get()
        trg_file = queue.get()
        definitive_alignments = queue.get()
        comparable_alignments = queue.get()

        # write alignments to xml file
        if args.comp:
            definitive_alignments.update(comparable_alignments)
            write_alignments_to_xml(
                definitive_alignments, src_file, trg_file, args.output)
        else:
            write_alignments_to_xml(
                definitive_alignments, src_file, trg_file, args.output)
            write_alignments_to_xml(
                comparable_alignments, src_file, trg_file, args.output[:-4]+"_comparable.xml")


################################################################################

if __name__ == "__main__":

    main()
