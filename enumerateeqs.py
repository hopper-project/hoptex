import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
from collections import Counter

def plsmath(filename):
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return grabmath(text)

def main():
    global outpath
    parser = argparse.ArgumentParser(description='Usage for equation enumeration1')
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    args = parser.parse_args()
    dirname = os.path.join(os.path.abspath(args.directory),'')
    outpath = os.path.abspath(args.outfile)
    matches = []
    for root, dirnames, filenames in os.walk(dirname):
        for filename in fnmatch.filter(filenames, '*.tex'):
            matches.append(os.path.join(root, filename))
    pool = mp.Pool(processes=mp.cpu_count())
    math_equations = pool.map(plsmath,matches)
    math_equations = pool.map(enumerate,math_equations)
    # at this point, the list should be of the form: (index, eqtext)
    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
