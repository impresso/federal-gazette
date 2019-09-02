#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""

"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
import re
from collections import Counter
from pathlib import Path
import spacy


def parse_args():
    """Parse the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-dir",
        required=True,
        action="store",
        help="input dir from which raw text files are read",
    )

    parser.add_argument(
        "-f_ne",
        required=True,
        action="store",
        help="output file to record all named entities",
    )

    parser.add_argument(
        "-l",
        "--lang",
        required=True,
        action="store",
        help="provide language for spacy model",
    )

    return parser.parse_args()


def doc_to_file(doc, f_out):
    """
    Write tokens into file, one sentence per line
    """
    with open(f_out, mode="w") as f:
        for sent in doc.sents:
            tokens = [tok.text for tok in sent]
            # naively limit maximal length of sentence
            # to avoid problems in machine translation
            max_length = 200
            for start in range(0, len(tokens), max_length):
                seq = " ".join(tokens[start : start + max_length])
                f.write(seq + "\n")


def entities_to_file(f_out, entities):
    """
    Write all entities into file, sorted by their frequency
    """
    entities = sorted(entities.items(), key=lambda kv: kv[1], reverse=True)
    with open(f_out, mode="w") as f:
        for ent, freq in entities:
            f.write("{}\t{}\n".format(ent, freq))


def preprocess_text(text):
    # remove page numbers
    text = re.sub(r"\d*\s*\f\s*\d*", "", text)

    # merge lines when the first line ends with a hyphen
    # and the second does not start with a 'und' or 'et' etc.
    text = re.sub(r"(?<=\w)-\s*\n\s*(und|et|oder|ou)\b", r"- \1", text, re.MULTILINE)
    text = re.sub(r"(?<=\w)-\s*\n\s*", r"", text, re.MULTILINE)

    # join lines with hard-line breaks
    text = re.sub(r"\n", " ", text)

    return text


def stream_files(fnames):
    """
    Iterate over given files and stream them
    """
    for fname in fnames:
        with open(fname, mode="r") as f:
            text = f.read()
            text = preprocess_text(text)

            yield text


def get_clean_entities(doc, concat_type=True):
    """
    Filter particular entity classes and trim entities
    """

    # entities that are considered
    ent_consider = {"PERSON", "ORG", "NORP", "GPE", "LOC"}

    pos_ignore = {"DET", "X", "SYM", "NUM"}

    entities = []

    for ent in doc.ents:

        # only consider particular entity types
        if ent.label_ not in ent_consider:
            continue

        # trim beginning of entity
        while len(ent) > 1 and (ent[0].pos_ in pos_ignore):
            ent[0].ent_type_ = ""  # remove entity tag the leading token
            ent = ent[1:]

        # trim end of entity
        while len(ent) > 1 and (ent[-1].pos_ in pos_ignore):
            ent[-1].ent_type_ = ""  # remove entity tag the trailing token
            ent = ent[:-1]

        ent_clean = ent.text

        if concat_type:
            ent_clean = ent_clean + "\t" + ent.label_

        print(ent_clean, [t.pos_ for t in ent])

        entities.append(ent_clean)

    return entities


def main():
    args = parse_args()

    print("\n", "=" * 40)
    print("\tCollecting filenames...")
    fnames = [str(fname) for fname in Path(args.dir).glob("**/*.text")]
    texts = stream_files(fnames)

    counter = Counter()

    if args.lang == "de":
        model = "de_core_news_md"
    elif args.lang == "fr":
        model = "fr_core_news_md"

    nlp = spacy.load(model)
    batch = 20
    print("\tLoaded spaCy model {}".format(model))

    print("\tStart processing of {} documents...".format(len(fnames)))
    for i, doc in enumerate(nlp.pipe(texts, batch_size=batch)):
        f_out = fnames[i].replace(".text", ".spacy.sent.txt")
        print(fnames[i])
        doc_to_file(doc, f_out)

        # extract named entities
        entities = get_clean_entities(doc)
        counter.update(entities)

        if i % 500 == 0 and i != 0:
            print("\t{} of {} documents are processed.".format(i, len(fnames)))

    entities_to_file(args.f_ne, counter)
    print("\n", "=" * 40)


################################################################################
if __name__ == "__main__":
    main()
