#!/usr/bin/python3
"""


"""

import sys
import codecs
import re
import os

from optparse import OptionParser


__author__ = "Simon Clematide"
__email__ = "siclemat@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2018"
__status__ = "development"


sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)

OPTIONS = {"sentfinal": "!.?"}


def process(a):
    sentfinal = set(OPTIONS['sentfinal'])
    with open(a, encoding='utf-8') as f:
        sent = []
        for i, l in enumerate(f):
            l = l.rstrip()
            if l != '':
                sent.append(l)
            if l in sentfinal or i > 250:
                # limit maximal length of sentence to avoid problems in machine translation
                print(' '.join(sent))
                sent = []

        # print the remainings of a sentence at the end of a document
        # this is is important for the disclaimer of confidential articles
        if len(sent) > 0:
            print(' '.join(sent))


def main(args):
    """
    """

    for a in args:
        process(a)


if __name__ == '__main__':

    parser = OptionParser(
        usage='%prog [OPTIONS] [ARGS...]',
        version='%prog 0.99',
        description='Download gazette federal files',
        epilog='Contact simon.clematide@uzh.ch'
    )
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=", OPTIONS, file=sys.stderr)

    main(args)
