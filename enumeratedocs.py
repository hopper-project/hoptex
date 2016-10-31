import argparse
import os
import multiprocessing as mp
from core.funcs import *
from multiprocessing import Manager
import multiprocessing as mp
from glob import glob

def substitute_eqid(filename):
    global eqdict
    global outpath
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    textlist = grab_math(text,split=True)
    for i, x in enumerate(textlist):
        if x in eqdict:
            textlist[i] = eqdict[x]
        else:
            textlist[i] = textlist[i].strip()
        newtext = '\n'.join(textlist)
        newtext = re.sub(r'(?s)\\begin\{eqnarray\}.+?\\end\{eqnarray\}|\\begin\{thebibliography\}.+|\$[^$]{1,50}\$|\\bibinfo\{.+?\}\{.+?\}|\\[A-z]+(?:\[.+?\])(?:\{.+?\})?|\\[A-z]+\{.+?\}|\\[A-z]+','',newtext).strip()
    with open(os.path.join(outpath,os.path.basename(filename)),mode='w',encoding='utf-8') as fh:
        fh.write(newtext)

def main():
    global eqdict
    global outpath
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("tsv", help="Path to .tsv of enumerated equations (output of enumerateeqs.py)")
    parser.add_argument("--parent", action='store_true', help="Use flag if the specified directory is the parent of .tex file directories")
    parser.add_argument("directory",help="Path to directory of .tex files, or demacro (if the flag is specified)")
    parser.add_argument("outpath",help="Path to output directory")
    args = parser.parse_args()
    tsv = os.path.abspath(args.tsv)
    directory = os.path.join(os.path.abspath(args.directory),'')
    outdir = os.path.join(os.path.abspath(args.outpath),'')
    parent = args.parent
    # folderlist = glob(directory+'*/')
    print("Generating equation dictionary...")
    eqdict = {}
    with open(tsv,mode='r',encoding='latin-1') as fh:
        for line in fh:
            eqid, equation = line.strip().split('\t')
            equation = equation.encode().decode('unicode_escape')
            if equation not in eqdict:
                eqdict[equation] = eqid
    print("Equation dictionary loaded.")
    if(parent):
        print("Iterating over folders in {}".format(directory))
        folderlist = next(os.walk(directory))[1]
        for subfolder in folderlist:
            outpath = os.path.join(outdir,subfolder)
            if not os.path.exists(outpath):
                os.makedirs(outpath)
            print("Finding .tex files in {}".format(subfolder))
            current_dir = os.path.join(directory,subfolder)
            filelist = getmathfiles(current_dir)
            print("Writing files...")
            pool = mp.Pool(processes=mp.cpu_count())
            pool.map(substitute_eqid,filelist)
            pool.close()
            pool.join()
    else:
        outpath = outdir
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        print("Finding all .tex files...")
        filelist = getmathfiles(directory)
        print("Writing files...")
        pool.map(substitute_eqid,filelist)
        pool.close()
        pool.join()

if __name__ == '__main__':
    main()
