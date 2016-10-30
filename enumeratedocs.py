import argparse
import os
import multiprocessing as mp
from core.funcs import *
from multiprocessing import Manager
import multiprocessing as mp

def substitute_equation_ids(text):
    split_list = grab_math(text,split=0)


def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("outpath",help="Path to output directory")
    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    outpath = os.path.join(os.path.abspath(args.outpath),'')
    print("Generating equation dictionary...")
    eqdict = {}
    with open('/media/jay/Data1/demacro_equation_out_new.tsv',mode='r',encoding='latin-1') as fh:
        for line in fh:
            eqid, equation = line.strip().split('\t')
            equation = equation.encode().decode('unicode_escape')
            if equation not in eqdict:
                eqdict[equation] = eqid
    print("Equation dictionary loaded.")
    print("Finding all .tex files...")
    filelist = getmathfiles('1506/')
    print("Outputting new .tex files")
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    for texfile in getmathfiles('1506/'):
        with open(texfile, mode='r',encoding='latin-1') as fh:
            text = fh.read()
        textlist = grab_math(text,split=True)
        for i, x in enumerate(textlist):
            if x in eqdict:
                textlist[i] = eqdict[x]
            else:
                textlist[i] = textlist[i].strip()
        newtext = '\n'.join(textlist)
        with open(os.path.join(outpath,os.path.basename(texfile)),mode='w',encoding='utf-8') as fh:
            fh.write(newtext)

if __name__ == '__main__':
    main()
