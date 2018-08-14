#!/usr/bin/python3

"""
Lemmatizer for creating/using a lemmatization JSON dictionary

This module implements a corpus-based global optimality-oriented lemmatization with coarse-grained POS tags.

There are 4 coarse-grained POS tags relevant for lemmatization (similar to single character codes of sketchengine):
 - N for nouns or not so well-known proper names
 - E for well-known proper names
 - J for adjective
 - V for verbs
 - P for pronouns (STTS P...)
 - D for articles (STTS ART)
 - A for adverbs (STTS ADV) there are a few ones with degree)
 - I for adpositions (STTS also APPRART)
 - X any other (no inflection performed on them) or TRUNC
 - _ if unspecified for unknown lemmas

The JSON lemmatization dictionary has the following format:
 - Each wordform W is an attribute A on the first level of the dictionary
 - The value V of attribute A is a list ordered by global lemma optimality.
 - The list V contains lists of length three where the first element is the lemma and the second element is the
   concatenation of all ordered single character codes of all possible POS tags, the third element is the frequency
   according to some corpus. For hyphenated words, the frequency is computed on the last part of the word.

Example::

    {
     'vermittelt': [
      [ 'vermitteln', 'V', 23 ],
      [ 'vermittelt', 'A', 22 ]
     ],
     'um': [
      [ 'um', 'AIX', 30000 ]
     ]
    }


## Lemmatization raw file format
The same WORDFORM may have several lemmas.
The LEMMA <unknown> may be used for unknown words.

WORDFORM TAB STTS TAB LEMMA

 - WORDFORM: inflected form
 - STTS: STTS POS Tag
 - LEMMA: Base form

Example::

[
  [
    "titelträg",
    "J",
    0,
    4894
  ],
  [
    "titelträge",
    "J",
    0,
    4894
  ],
  [
    "Titelträger",
    "N",
    2447,
    2579
  ]
]

"""

import codecs
import re
import sys
import json
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

# All explcit mappings. The rest goes into category X
STTS2SHORT = {
    'ADJA': 'J',
    'ADJD': 'J',
    'ADV': 'A',
    'APPO': 'I',
    'APPR': 'I',
    'APPRART': 'I',
    'APZR': 'I',
    'ART': 'D',
    'FM': 'X',
    'NE': 'E',
    'NN': 'N',
    'NNE': 'N',
    'PDAT': 'P',
    'PDS': 'P',
    'PIAT': 'P',
    'PIDAT': 'P',
    'PIS': 'P',
    'PPER': 'P',
    'PPOSAT': 'P',
    'PPOSS': 'P',
    'PRELAT': 'P',
    'PRELS': 'P',
    'PRF': 'P',
    'PWAT': 'P',
    'PWAV': 'P',
    'PWS': 'P',
    'TRUNC': 'X',
    'VVFIN': 'V',
    'VVIMP': 'V',
    'VVINF': 'V',
    'VVIZU': 'V',
    'VVPP': 'V',
    'VAFIN': 'V',
    'VAIMP': 'V',
    'VAINF': 'V',
    'VAPP': 'V',
    'VMFIN': 'V',
    'VMINF': 'V',
    'VMPP': 'V',
}

STOPWORDPOS =  {
    '$.': 'X',
    '$,': 'X',
    '$(': 'X',
    'ADV': 'A',
    'APPO': 'I',
    'APPR': 'I',
    'APPRART': 'I',
    'APZR': 'I',
    'ART': 'D',
    'CARD':'X',
    'KOUS':'X',
    'KOUI': 'X',
    'KON':'X',
    'KOKOM': 'X',
    'PDAT': 'P',
    'PDS': 'P',
    'PIAT': 'P',
    'PIDAT': 'P',
    'PIS': 'P',
    'PPER': 'P',
    'PPOSA': 'P',
    'PPOSS': 'P',
    'PRELA': 'P',
    'PRELS': 'P',
    'PRF': 'P',
    'PWAT': 'P',
    'PWAV': 'P',
    'PAV': 'P',
    'PWS': 'P',
    'PTKVZ': 'X',
    'PTKANT': 'X',
    'PTKA': 'X',
    'PTKZU': 'X',
    'TRUNC': 'X',
    'VAFIN': 'V',
    'VAIMP': 'V',
    'VAINF': 'V',
    'VAPP': 'V',
    'VMFIN': 'V',
    'VMINF': 'V',
    'VMPP': 'V',
}
OPTIONS = {}
LEMMATIZATION = {} # map WORDFORM -> (LEMMA * POS) List | LEMMA
FREQDIST = defaultdict(int)
LEMMAFREQDIST = defaultdict(int) # Number of times this lemmatization was derived
LCWORDFORMS2OTHER = defaultdict(set)
STATS = Counter()
STOPWORDS = set()
def map_stts_to_short(tag):
    """

    :param tag:
    :return:
    """
    return STTS2SHORT.get(tag,'X')

def uccase_factor(wf,lemma):
    """
    Return coefficient that boosts a lemma if both are uppercase
    :param wf:
    :param lemma:
    :return:
    """
    if lemma[0].isupper() and wf[0].isupper():
        return 20
    else:
        return 1

def read_freq_file(file):
    """

    :param file:
    :return:
    """
    FREQDIST = Counter()
    with codecs.open(file,'r',encoding="utf-8") as f:
        for l in f:
            d = l.rstrip().split('\t')
            if len(d) != 2:
                print('#WARNING-FORMAT-ERROR', l, file=sys.stderr)
                continue
            freq, wf = d
            if OPTIONS.get('shorten_lemma') and '-' in wf:
                wf = shorten_to_hyphen(wf, minimum=3)

            FREQDIST[wf] += int(freq)
#            wflower = wf.lower()
#            if wflower != wf:
#                LCWORDFORMS2OTHER[wflower].add(wf)
    print('#INFO-FREQDIST-FILE-LOADED', file, file=sys.stderr)
    print('#INFO-SIZE-OF-FREQDIST-DICT', len(FREQDIST), file=sys.stderr)
    return FREQDIST

def read_json_file(file):
    global LEMMATIZATION
    with codecs.open(file,'r',encoding='utf-8') as f:

        LEMMATIZATION = json.load(f)
    return LEMMATIZATION

def read_lemma_file(file):
    """
    Return data structure containing the information of the GERTWOL output.

    :param file:
    :return:

    Sample input
Liquidationsvergleich   NN      Liquidationsvergleich
Elektro-Einzüger        NN      Elektro-Einzüger
    """
    stats = Counter()
    all_lemmas = defaultdict(dict)
    with codecs.open(file,'r',encoding="utf-8") as f:
        for l in f:
            d = l.rstrip().split('\t')
            if len(d) < 2:
                print('#LINE-PROBLEM', l, d, file=sys.stderr)
                stats['LINEPROBLEM'] += 1
                continue
            wf, pos, lemma = d
            if pos in STOPWORDPOS and OPTIONS['filter_stopwords']:
                STOPWORDS.add(wf)
                stats['STOPPWORD-WORDFORM'] += 1

                continue
            if re.match(r"""[+-]\d+([',.]+\d+)*$""",wf):
                stats['DIGIT'] += 1
                print('#INFO-DIGITLIKE-TOKEN-FILTERED', wf, FREQDIST[wf], file=sys.stderr)
                continue
            if d[2] == '<unknown>':
                stats['UNK'] += 1
                print('#INFO-UNKNOWN-TOKEN-FILTERED', wf, FREQDIST[wf], file=sys.stderr)
                continue

            if OPTIONS['shorten_lemma'] and "-" in lemma:
                lemma_ = shorten_to_hyphen(lemma, minimum=3)
                if lemma != lemma_:
                    print('#INFO-SHORTEN-LEMMA',lemma, lemma_, file=sys.stderr)
                    lemma = lemma_
            if d[2] not in all_lemmas[d[0]]:
                all_lemmas[wf][lemma] = {map_stts_to_short(pos)}  # map WORDFORM => LEMMA => STTS set
            else:
                all_lemmas[wf][lemma].add(map_stts_to_short(pos))
            LEMMAFREQDIST[lemma] += FREQDIST[wf]
            if wf != lemma:
                stats['DIFFLEMMA'] += 1
            else:
                stats['EQLEMMA'] += 1

    for wf in all_lemmas:
        for lemma in all_lemmas[wf]:

            all_lemmas[wf][lemma] = "".join(sorted(all_lemmas[wf][lemma]))

    print(stats,file=sys.stderr)
    return all_lemmas

def shorten_to_hyphen(word, minimum=0, digits=True):
    """
    Return word shortened after the last hyphen or slash

    :param word: str
    :return: None if STOPWORD else str
    """


    if digits:
        word = re.sub(r'\d+','#',word)
    if '-' in word:
        word_ = re.sub(r'^.*[-/]([^/-]{2,})$', r'\1',word)
        if minimum > 0 and len(word) >= minimum:
            return word_
        else:
            return word
    else:
        return word


def filter_lemmas(wf, freqlist):
    """
    List ist sorted in decreasing order

    :param wf:
    :param freqlist:
    :return:
    """
    mostfreq = 0
    result = []
    accepted = set()
    for i, (minfreq, lfreq, wfreq, lemma, postag, shortlemma) in enumerate(freqlist):

        if wfreq > mostfreq:
            mostfreq = wfreq
            result.append([lemma,postag, wfreq, lfreq])
            accepted.add(lemma)
            STATS['INCLUDED'] += 1
        else:

            if wfreq == 0 and mostfreq > 1 and wf in accepted and not 'V' in postag:
                print('#INFO-FILTERED-AMBIGUOUS-LEMMA', wf, wfreq, lemma, lfreq, result, file=sys.stderr)
                STATS['FILTERED'] += 1
                continue
            result.append([lemma, postag, wfreq, lfreq])
    return result

def order_lemmas(wf, lemmas):
    """
    Return the best lemma according to the following criterion

    :param wf:
    :param lemmas:
    :return:

lemmas::
    {'vorausbestimmen': 'V', 'vorausbestimmt': 'J'}


    """
   # if wf.isupper():
       # pass
    sorted_lemmas = []
    for x in lemmas:
        lemmafreq = LEMMAFREQDIST[x]
        wordfreq = FREQDIST[shorten_to_hyphen(x)]
        minfreq = min(lemmafreq, wordfreq)*uccase_factor(wf,x)
        sorted_lemmas.append((minfreq,lemmafreq,wordfreq,x,lemmas[x],shorten_to_hyphen(x)))
        sorted_lemmas.sort(reverse=True)

    selected_lemmas = filter_lemmas(wf, sorted_lemmas)
    #print(selected_lemmas, file=sys.stderr)
    return selected_lemmas

def thin_lemmas(all_lemmas):
    """

    :param all_lemmas:
    :return:
    """
    for wf in all_lemmas:
        #print(wf, all_lemmas[wf])
        pos_lemma_dict = all_lemmas[wf]
        # if there is only ONE possible lemmatization, go with it!
        if len(pos_lemma_dict) == 1:
            key = list(pos_lemma_dict)[0]
            freq = FREQDIST[shorten_to_hyphen(key)]
            LEMMATIZATION[wf] = [[key,pos_lemma_dict[key], freq, LEMMAFREQDIST[key]]]
            #print(wf, LEMMATIZATION[wf],file=sys.stderr)
        else:
            result = order_lemmas(wf,pos_lemma_dict)
            LEMMATIZATION[wf] = result
            #uppercase_lemmas = [x[1] for x in pos_lemma_list if wf[0].is]



def main(args):
    """
    Given a main html index file from www.admin.ch  convert all HTML files to tsv files
    :param input_dir: directory containing tetml files
    :param row_hint: define which Element in the XML tree contains one text row
    :return:
    """

    # First read the frequency file (needed for processing the lemmatization file)
    global FREQDIST
    if OPTIONS['frequency_file']:
        FREQDIST = read_freq_file(OPTIONS['frequency_file'])
    if OPTIONS['lemmatization_file']:
        all_lemmas = read_lemma_file(OPTIONS['lemmatization_file'])
        thin_lemmas(all_lemmas)

    # print(LEMMATIZATION)
    if OPTIONS['mode'] == 'json':
        json.dump(LEMMATIZATION,sys.stdout,ensure_ascii=False, sort_keys=True, indent=0)
    elif OPTIONS['mode'] == 'simplelem':
        min_token_len = OPTIONS['minimal_token_length']
        for l in sys.stdin:
            tokens = l.rstrip().split()

            tokens_ = []
            for t in tokens:
                t_ = shorten_to_hyphen(t,minimum=3)
                if not t_ is None:
                    tokens_.append(t_)
            if OPTIONS['filter_stopwords']:
                tokens = [t for t in tokens if not t in STOPWORDS]
            if OPTIONS['shorten_lemma']:
                tokens = [shorten_to_hyphen(t,minimum=3) for t in tokens]
            lemmas = []
            for t in tokens:
                if len(t) < min_token_len:
                    STATS['#MIN-TOKEN-LENGTH-NOT-REACHED'] += 1
                    continue
                linfo = LEMMATIZATION.get(t)
                if linfo:
                    l = linfo[0][0]
                    if len(l) >= min_token_len:
                        lemmas.append(linfo[0][0])
                else:
                    lemmas.append(t)
            print(" ".join(lemmas))

    print(STATS, file=sys.stderr)

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
                      action='store', dest='mode', default='json',type=str,
                      help='action mode: json = emit lemmatization dictionary on stdout; lemmatize = apply lemmatization (%default)')
    parser.add_option('-L', '--lemmatization_file',
                      action='store', dest='lemmatization_file', default=None,
                      help='lemmatization file (needed) (%default)')
    parser.add_option('-J', '--json_file',
                      action='store', dest='json_file', default=None,
                      help='JSON file  (%default)')
    parser.add_option('-F', '--frequency_file',metavar="FILE",
                      action='store', dest='frequency_file', default=None,
                      help='frequency file (needed) (%default)')
    parser.add_option('-H', '--shorten_lemma',
                      action='store_true', dest='shorten_lemma', default=False,
                      help='shorten word forms and lemmas with hyphens (%default)')
    parser.add_option('-I', '--ignore_pos_tags',
                      action='store', dest='ignore_pos_tags', default=None,
                      help='double-underscore separated list of ignored POS; superseeds the normal stopword criterion based POS tags(%default)')
    parser.add_option('-S', '--filter_stopwords',
                      action='store_true', dest='filter_stopwords', default=False,
                      help='Filter stopwords if true (%default)')
    parser.add_option('-T', '--minimal_token_length',
                      action='store', dest='minimal_token_length', default=3,
                      help='minimal lemma length kept (%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)
    if OPTIONS['json_file']:
        read_json_file(OPTIONS['json_file'])
    if not OPTIONS['lemmatization_file']:
        print('WARNING: No lemmatization file provided! No lemmatization will be conducted!')
    main(args)
