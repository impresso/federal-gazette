#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Alex Flückiger <alex.flueckiger@uzh.ch>'

# imported modules
import argparse  # programm argument handling
import glob


def parse_args():
    """Parses the arguments given with program call"""

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input',  required=True, action='store',
                        dest='input_dir', help='input folder with txt-documents')
    parser.add_argument('-o', '--output', required=True,
                        action='store', dest='out_file', help='output file that collects all sentences of each article')

    return parser.parse_args()


def main():
    """
    Restructure all cuttered documents of a given input dir and
    write their sentences into a single txt
    """

    # parse arguments
    args = parse_args()
    input_dir = args.input_dir
    if input_dir[:-1] != '/':
        input_dir += '/'

    # create outfile name
    outfile = args.out_file

    with open(outfile, mode='w', encoding='utf-8') as f_out:
        # write file or dir id
        f_out.write('{}\n'.format(input_dir))

        # iterate over relevant files in the given input folder
        for infile in glob.iglob(input_dir+'/**/*cuttered.sent.txt', recursive=True):

            with open(infile, mode='r', encoding='utf-8') as f_in:
                # write article id
                f_out.write(infile + '\n')
                for line in f_in:
                    f_out.write(line.strip() + '\n')

                f_out.write('.EOA\n')
        f_out.write('.EOB\n')


if __name__ == '__main__':

    main()
