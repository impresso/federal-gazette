#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Evaluate multivec model with some sample words
"""

__author__ = "Alex Flückiger"
__email__ = "alex.flueckiger@uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2019"
__status__ = "development"


import argparse
from multivec import MonolingualModel, BilingualModel
import numpy


def parse_args():
    """parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model", required=True, help="path to binary file of bilingual model"
    )

    return parser.parse_args()


def evaluate_multivec(model):
    """Evaluate multivec model by computing cosinus distance with some sample pairs"""

    model = BilingualModel(model)

    test_vocab = [
        ("frankreich", "france"),
        ("schweiz", "suisse"),
        ("der", "le"),
        ("name", "nom"),
        ("bundesrat", "kanton"),
    ]

    for src, trg in test_vocab:
        src_vec = model.src_model.word_vec(src)
        trg_vec = model.trg_model.word_vec(trg)
        cos_sim = numpy.dot(src_vec, trg_vec) / (
            numpy.linalg.norm(src_vec) * numpy.linalg.norm(trg_vec)
        )
        print("{} : {} ({:.3f})".format(src, trg, cos_sim))


def main():

    # parse arguments
    args = parse_args()

    evaluate_multivec(args.model)


################################################################################
if __name__ == "__main__":

    main()
