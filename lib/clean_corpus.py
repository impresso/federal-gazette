#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Clean a parallel corpus file containing sentence pairs separated by a tab.

This script is based on the cleaning script provided by the Moses Toolkit:
https://github.com/moses-smt/mosesdecoder/blob/master/scripts/training/clean-corpus-n.perl

Usage:
    lib/clean_corpus.py --f_in=<fpath> --f_out=<fpath> [options]

Options:
    -h --help                   Show this screen.
    -i --f_in=<fpath>           File with parallel sentences (tsv format).
    -o --f_out=<fpath>          File with clean, parallel sentences (tsv format).
    --min_token=<float>         Keep only sentence pairs with a minimum number of tokens [default: 5].
    --max_token=<float>         Keep only sentence pairs with a maximum number of tokens [default: 150].
    --min_chars=<float>         Keep only sentence pairs with a minimum string length [default: 30].
    --max_chars=<float>         Keep only sentence pairs with a maximum string length  [default: 700].
    --length_ratio=<float>  Keep only sentence pairs up to a certain ratio based on their lengths [default: 1.6].
    --digit_ratio=<float>   Keep only sentence pairs if the number of digits is below a certain ratio [default: 0.2].

"""

from docopt import docopt


def read_parallel_sentences(f_in, delimiter='\t'):

    with open(f_in, mode="r", encoding="utf-8-sig") as f:
        for line in f:
            src_sent, trg_sent = line.strip().split(delimiter)
            yield src_sent, trg_sent


def filter_by_string_length(src, trg, min_chars, max_chars,):
    n_src = len(src)
    n_trg = len(trg)

    #print('hit_length', n_src, n_trg,min_chars, max_chars )
    #print(all([n_src, n_trg]) > min_chars)
    #print(all([n_src, n_trg]) < max_chars)

    return (n_src < min_chars or n_trg < min_chars) and (n_src > max_chars or n_trg > max_chars)



def filter_by_token_length(src, trg, min_token, max_token):

    n_src = len(src.split(' '))
    n_trg = len(trg.split(' '))

    return (n_src < min_token or n_trg < min_token) or (n_src > max_token or n_trg > max_token)



def filter_by_length_ratio(src, trg, max_ratio):
    ratio_src2trg = len(src) / len(trg)
    ratio_trg2src = len(trg) / len(src)

    return max([ratio_src2trg, ratio_trg2src]) > max_ratio


def filter_by_digit_ratio(src, trg, max_ratio):

    ratio_src_digits = sum(c.isdigit() for c in src) / len(src)
    ratio_trg_digits = sum(c.isdigit() for c in trg) / len(trg)

    return max([ratio_src_digits, ratio_trg_digits]) > max_ratio


def main(args):

    f_in = args["--f_in"]
    f_out = args["--f_out"]
    min_chars = int(args["--min_chars"])
    max_chars = int(args["--max_chars"])
    min_token = int(args["--min_token"])
    max_token = int(args["--max_token"])
    length_ratio = float(args["--length_ratio"])
    digit_ratio = float(args["--digit_ratio"])

    parallel_sents = read_parallel_sentences(f_in)


    print('Cleaning parallel corpus:', f_in)
    print(f'Number of characters: {min_chars} - {max_chars}')
    print(f'Number of tokens: {min_token} - {max_token}')
    print('Maximum portion of digits:', digit_ratio)
    print('Maximum crosslingual length ratio:', length_ratio)

    n_clean = 0

    with open(f_out, mode="w") as f:

        for idx, (src, trg) in enumerate(parallel_sents):

            # skip pair if one of the criteria don't match and not delimiter
            if not any(d in src for d in ['.EOA', '.EOB']):
                if filter_by_string_length(src, trg, min_chars, max_chars):
                    continue
                if filter_by_token_length(src, trg, min_token, max_token):
                    continue
                if filter_by_length_ratio(src, trg, length_ratio):
                    continue
                if filter_by_digit_ratio(src, trg, digit_ratio):
                    continue


            line = "\t".join([src, trg])
            f.write(line + "\n")
            n_clean += 1

    print('Save cleaned parallel corpus:', f_out)
    ratio_sent = n_clean / idx
    print(f'Number of sentences before and after cleaning: {idx} / {n_clean} ({ratio_sent:.2f})')


if __name__ == "__main__":
    arguments = docopt(__doc__)
    main(arguments)
