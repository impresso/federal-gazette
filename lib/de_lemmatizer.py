#!/usr/bin/python3
"""
Lemmatizer using a lemmatization file

Using the shortest lemma compatible with the casing information.
If WORDFORM starts with uppercase, then only the STTS POS Lemmas NN or NE are used.
If WORDFORMS starts with lowercase then only the STTS POS Lemmas with other tags than NN or NE are considered (if any).

## Lemmatization file format
The same WORDFORM may have many lemmas.
The LEMMA <unknown> may be used for unknown words.

WORDFORM TAB STTS TAB LEMMA

 - WORDFORM: inflected form
 - STTS: STTS POS Tag
 - LEMMA: Base form

"""

import sys, codecs,re
import os
from collections import Counter, defaultdict
from optparse import OptionParser



__author__ = "Simon Clematide"
__email__ = "siclemat@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2018"
__status__ = "development"



sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)

OPTIONS = {}
LEMMATIZATION = {} # map WORDFORM -> LEMMA
FREQDIST = defaultdict(int)
LCWORDFORMS2OTHER = defaultdict(set)


def read_freq_file(file):
    global FREQDIST, LCWORDFORMS2OTHER
    with codecs.open(file,'r',encoding="utf-8") as f:
        for l in f:
            d = l.rstrip().split('\t')
            if len(d) < 2:
                continue
            freq, wf = d
            FREQDIST[wf] = int(freq)
            wflower = wf.lower()
            if wflower != wf:
                LCWORDFORMS2OTHER[wflower].add(wf)
    print('#INFO-FREQDIST-FILE-LOADED', file, file=sys.stderr)
    print('#INFO-SIZE-OF-FREQDIST-DICT', len(FREQDIST), file=sys.stderr)


def read_lemma_file(file):
    stats = Counter()
    all_lemmas = defaultdict(dict)
    with codecs.open(file,'r',encoding="utf-8") as f:
        for l in f:
            d = l.rstrip().split('\t')
            if len(d) < 2:
                print('#LINE-PROBLEM', l, d, file=sys.stderr)
                continue
            if d[2] == '<unknown>':
                stats['UNK'] += 1
                continue
            if d[2] not in all_lemmas[d[0]]:
                all_lemmas[d[0]][d[2]] = set([d[1]]) # map WORDFORM => LEMMA => STTS set
            else:
                all_lemmas[d[0]][d[2]].add(d[1])
            if d[0] != d[2]:
                stats['DIFFLEMMA'] += 1
            else:
                stats['EQLEMMA'] += 1

    print(stats,file=sys.stderr)
    return all_lemmas

def shorten_to_hyphen(word):
    ""
    if '-' in word:
        return re.sub(r'^.+-([^-]{2,})$',r'\1',word)
    else:
        return word

def select_lemma(wf, lemmas):
    """
    Return the best lemma according to the following criterion


    """
    if wf.isupper():
        pass

    shortest_lemmas = sorted((-FREQDIST[shorten_to_hyphen(x)],len(x),x,shorten_to_hyphen(x)) for x in lemmas)
    print('#SORTED LEMMAS',shortest_lemmas)
    for freq,length,lemma,shortlemma in shortest_lemmas:
        if lemma != shortlemma or True:
            print(wf,-freq,length,lemma,shortlemma,FREQDIST[shortlemma])
  #      if lemma in FREQDIST:
  #          print(wf, lemma,FREQDIST[lemma])
    #for lemma in lemmas:




def thin_lemmas(all_lemmas):
    for wf in all_lemmas:
        #print(wf, all_lemmas[wf])
        pos_lemma_dict = all_lemmas[wf]
        # if there is only ONE possible lemmatization, go with it!
        if len(pos_lemma_dict) == 1:
            key = list(pos_lemma_dict)[0]
            if key != wf:
                LEMMATIZATION[wf] = key
                #print(wf, LEMMATIZATION[wf],file=sys.stderr)
        else:
            select_lemma(wf,pos_lemma_dict)
            #print(wf,pos_lemma_dict)
            #uppercase_lemmas = [x[1] for x in pos_lemma_list if wf[0].is]



def main(args):
    """
    Given a main html index file from www.admin.ch  convert all HTML files to tsv files
    :param input_dir: directory containing tetml files
    :param row_hint: define which Element in the XML tree contains one text row
    :return:
    """
    if OPTIONS['frequency_file']:
        read_freq_file(OPTIONS['frequency_file'])
    if OPTIONS['lemmatization_file']:
        all_lemmas = read_lemma_file(OPTIONS['lemmatization_file'])
        thin_lemmas(all_lemmas)


if __name__ == '__main__':

    parser = OptionParser(
        usage = '%prog [OPTIONS] ',
        version='%prog 0.99', #
        description='Deterministically lemmatize tokenized German texts',
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
    parser.add_option('-m', '--mode',
                      action='store', dest='mode', default='wget',type=str,
                      help='output wget: Emit wget commands for missing files (%default)')
    parser.add_option('-L', '--lemmatization_file',
                      action='store', dest='lemmatization_file', default=None,
                      help='lemmatization file (needed) (%default)')
    parser.add_option('-F', '--frequency_file',
                      action='store', dest='frequency_file', default=None,
                      help='frequency file (needed) (%default)')
    parser.add_option('-I', '--ignore_pos_tags',
                      action='store', dest='ignore_pos_tags', default="CARD",
                      help='double-underscore separated list of ignored POS tags(%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)
    if not OPTIONS['lemmatization_file']:
        print('WARNING: No lemmatization file provided! No lemmatization will be conducted!')
    main(args)
