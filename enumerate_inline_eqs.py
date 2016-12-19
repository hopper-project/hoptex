"""Script for enumeration of inline math equations"""
import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
from collections import Counter
import time

def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory", help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    parser.add_argument("--xhtml", help="Path to directory of xhtml files")
    parser.add_argument("--tsv", help="TSV to continue building off of")
    parser.add_argument("--parent", action="store_true", help="Use if this is the parent directory of multiple .tex files")
    args = parser.parse_args()
    xhtml = args.xhtml
    outfile = args.outfile
    parent = args.parent
    directory = os.path.join(os.path.abspath(args.directory),'')
    if(parent):
        folderlist = next(os.walk(directory))[1]
        matches = []
        for subfolder in folderlist:
            print("Finding .tex files in {}".format(subfolder))
            current_dir = os.path.join(directory,subfolder)
            matches += gettexfiles(current_dir)
    else:
        matches = gettexfiles(directory)
    print("Found {} files".format(len(matches)))
    if(xhtml):
        pass
    pool = mp.Pool(processes=mp.cpu_count())
    print("Grabbing math from files...")
    unique_eqs = set()
    eqcount = 0
    filecount = 0
    math_equations = pool.imap(grab_inline_math_from_file,matches)
    with open(outfile,'w') as fh:
        for doceqs in math_equations:
            for equation in doceqs:
                if equation not in unique_eqs:
                    eqid = "EQI" + str(eqcount) + "Q"
                    unique_eqs.add(equation)
                    fh.write(eqid + '\t' + repr(equation)[1:-1].replace("\t","\\t")+'\n')
                    eqcount += 1
            filecount += 1
    print("{} unique equations".format(len(unique_eqs)))
    print(eqcount)

if __name__=='__main__':
    main()
