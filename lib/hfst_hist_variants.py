#!/usr/bin/python3
"""


"""

import sys, codecs, os, re
import hfst
#print(sys.path)
import json
from collections import Counter, defaultdict
from optparse import OptionParser
from de_lemmatizer  import STOPWORDS, STOPWORDPOS, FREQDIST , LEMMATIZATION,\
     read_freq_file, shorten_to_hyphen, map_stts_to_short, read_lemma_file,read_json_file

DIR = os.path.dirname(os.path.realpath(__file__))



__author__ = "Simon Clematide"
__email__ = "siclemat@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2018"
__status__ = "development"



#sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
#sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
#sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)

OPTIONS = {}
LEMMATIZATION = {} # map WORDFORM -> (LEMMA * POS) List | LEMMA

LEMMAFREQDIST = defaultdict(int) # Number of times this lemmatization was derived
LCWORDFORMS2OTHER = defaultdict(set)
STATS = Counter()
OLDWORDFREQDIST = Counter()
NEWWORDFREQDIST = Counter()


def get_att_transducer(f):
    with open(f, 'r',encoding='utf-8') as f:
        try:
            r = hfst.AttReader(f)
            for tr in r:
                return tr
        except hfst.exceptions.NotValidAttFormatException as e:
            print(e.what(), file=sys.stderr)


def process(a):
    pass

def get_old_vocab():

    oldvoc = OLDWORDFREQDIST - NEWWORDFREQDIST
    return oldvoc

def get_hfst_transducer(name):
    hfstpath = os.path.join(DIR, name +'.hfst')
    attpath = os.path.join(DIR, name +'.att')
    hfst.set_default_fst_type(hfst.ImplementationType.FOMA_TYPE)
    hfst.compile_xfst_file(hfstpath, output=sys.stderr)
    tr = get_att_transducer(attpath)
    tr.lookup_optimize()
    return tr

def ocr_variants(file):
    OLDVOCAB = get_old_vocab()
    tr = get_hfst_transducer(file)
    for w,c in OLDVOCAB.most_common():
        if c < 3:
            continue
        if w in LEMMATIZATION and LEMMATIZATION[w][0][2] > 20:
            continue
        if re.match(r"""[+-]\d+([',.]+\d+)*$""", w):
            continue
        #if FREQDIST[w] > 100 or OLDVOCAB[w] > 3:
         #   print('#INFO-WORD-TO-OCRCORRECT', w, file=sys.stderr)
        result = []
        for resul in tr.lookup(w):
            wf_var = resul[0]

            if wf_var in LEMMATIZATION:
                # print('#INFO-WORD-TO-OCRCORRECT', OLDWORDFREQDIST[w], w, wf_var, LEMMATIZATION[wf_var], file=sys.stderr)
                #print(FREQDIST[w], w, LEMMATIZATION[wf_var], OLDWORDFREQDIST[w])
                result.append(LEMMATIZATION[wf_var][0])

        if not result:
            print('#INFO-OCRSPELL-NOT-FOUND',FREQDIST[w], w, file=sys.stderr)
        else:
            STATS['OCR'] += 1
            print('#INFO-WORD-TO-OCRCORRECT', OLDWORDFREQDIST[w], w, result, file=sys.stderr)
            result = order_hist_lemmas(result)
            LEMMATIZATION[w] = result
    return LEMMATIZATION






def histo_variants(file):
    """
    Normalize historic variants into already known words and map them to their possible lemmatization

    Enrich the LEMMATIZATION data structure accordingly and return it.

    :param file:
    :return:
    """

    OLDVOCAB = get_old_vocab()
    global STATS

    tr = get_hfst_transducer('fg_spelling_normalization')
    #for l in sys.stdin:
    #    w = l.rstrip().split('\t')[0]
    for w,c in OLDVOCAB.most_common():
        if w in LEMMATIZATION:
            continue
        if re.match(r"""[+-]\d+([',.]+\d+)*$""", w):
            continue
        #if not w in OLDVOCAB:
        #    print('#INFO-NOT-OLDVOCAB', w, file=sys.stderr)
        #    continue
        #if w in LEMMATIZATION:
        #    continue

        if FREQDIST[w] > 100 or c > 3:
            print('#INFO-WORD-TO-RESPELL', c, w, file=sys.stderr)

            result = []
            for resul in  tr.lookup(w):
                wf_var = resul[0]
                if wf_var == w:
                    continue

                if wf_var in LEMMATIZATION:

                   # print(FREQDIST[w], w, LEMMATIZATION[wf_var],OLDWORDFREQDIST[w])
                    found = True
                    linfo = LEMMATIZATION[wf_var]
                    #lemma = linfo[0]
                   # pos = linfo[1]
                   # mwfreq = linfo[2]
                   # mlfreq = linfo[3]
                    #d = {'lemma': lemma,
                         #'wfreq': OLDWORDFREQDIST[w]+NEWWORDFREQDIST[w],
                         #'ofreq': OLDWORDFREQDIST[w],
                         #'pos' : pos,
                         #'mwfreq': wfreq,
                        # 'mlfreq':mlfreq
                       #  }
                    if not LEMMATIZATION[wf_var][0] in result:

                        result.append(LEMMATIZATION[wf_var][0])

            if not result:
                print('#INFO-FREQUENT-NOT-FOUND',FREQDIST[w], w, file=sys.stderr)
            else:
                STATS['HISTO'] += 1
                print('#INFO-FREQUENT-FOUND', c, w, result, file=sys.stderr)
                result = order_hist_lemmas(result)
                LEMMATIZATION[w] = result

    return LEMMATIZATION


def order_hist_lemmas(result):
    """
    Order list of [LEMMA, WFREQ, LFREQ] by WFREQ in DESC order.
    :param result:
    :return:
    """
    result.sort(reverse=True,key=lambda x: x[2])
    return result
def main(args):
    """
    """

    # First read the frequency file (needed for processing the lemmatization file)
    global FREQDIST, LEMMATIZATION

    if OPTIONS['frequency_file']:
        FREQDIST = read_freq_file(OPTIONS['frequency_file'])
    LEMMATIZATION = histo_variants(None)
    LEMMATIZATION = ocr_variants('fg_ocr_correction')

    if OPTIONS['mode'] == "hjson":
        json.dump(LEMMATIZATION, sys.stdout, ensure_ascii=False, sort_keys=True)
        exit(0)
    if OPTIONS['lemmatization_file']:
        all_lemmas = read_lemma_file(OPTIONS['lemmatization_file'])




if __name__ == '__main__':

    parser = OptionParser(
        usage = '%prog [OPTIONS] [ARGS...]',
        version='%prog 0.99', #
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

    parser.add_option('-m', '--mode',
                      action='store', dest='mode', default='hjson',type=str,
                      help='action mode: json = emit lemmatization dictionary on stdout (%default)')
    parser.add_option('-L', '--lemmatization_file',
                      action='store', dest='lemmatization_file', default=None,
                      help='lemmatization file (needed) (%default)')
    parser.add_option('-J', '--json_file',
                      action='store', dest='json_file', default=None,
                      help='JSON file  (%default)')
    parser.add_option('-F', '--frequency_file',metavar="FILE",
                      action='store', dest='frequency_file', default=None,
                      help='frequency file (needed) (%default)')
    parser.add_option('-O', '--old_frequency_file',metavar="FILE",
                      action='store', dest='old_frequency_file', default=None,
                      help='old_frequency_file  (%default)')
    parser.add_option('-N', '--new_frequency_file',metavar="FILE",
                      action='store', dest='new_frequency_file', default=None,
                      help='new_frequency_file  (%default)')

    parser.add_option('-H', '--shorten_lemma',
                      action='store_true', dest='shorten_lemma', default=False,
                      help='shorten word forms and lemmas with hyphens (%default)')
    parser.add_option('-I', '--ignore_pos_tags',
                      action='store', dest='ignore_pos_tags', default=None,
                      help='double-underscore separated list of ignored POS; superseeds the normal stopword criterion based POS tags(%default)')
    parser.add_option('-T', '--minimal_token_length',
                      action='store', dest='minimal_token_length', default=3,
                      help='minimal lemma length kept (%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)

    if OPTIONS['json_file']:
        LEMMATIZATION = read_json_file(OPTIONS['json_file'])

    if OPTIONS['old_frequency_file']:
        OLDWORDFREQDIST = read_freq_file(OPTIONS['old_frequency_file'])

    if OPTIONS['new_frequency_file']:
        NEWWORDFREQDIST = read_freq_file(OPTIONS['new_frequency_file'])

    if not OPTIONS['lemmatization_file']:
        print('WARNING: No lemmatization file provided! No lemmatization will be conducted!' , file=sys.stderr)
    main(args)
