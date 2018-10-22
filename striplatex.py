"""Module for removing LaTeX code from .tex files"""

import argparse
import os
import multiprocessing as mp
from core.funcs import *
from multiprocessing import Manager
import multiprocessing as mp
from glob import glob
import shutil

def cleanfile(filename):
    """Function to be used with pool.map() in main"""
    global outpath
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    mathmatches = grab_math(text)
    for match in mathmatches:
        text = text.replace(match,"")
    text = re.sub(r'\\begin\{title\}(.+?)\\end\{title\}',r'\1',text)
    text = re.sub(r'(?s)\\begin\{picture\}.+?\\end\{picture\}','',text)
    text = re.sub(r'\\def.+','',text)
    text = re.sub(r'\\section\*?\{(.+?)\}',r'\1',text)
    text = re.sub(r'\\def.+|\\\@ifundefined.+|(?s)\\begin\{thebibliography\}.+?\\end\{thebibliography\}|(?s)\\begin\{eqnarray\*?\}.+?\\end\{eqnarray\*?\}|\\[\w@]+(?:\[.+?\])?(?:\{.+?\})*|\[.+?\](?:\{.+?\})?|\{cm\}','',text)
    text = re.sub(r'\}','',text)
    text = re.sub(r'\{','',text)
    text = re.sub(r'\(\)','',text)
    text = re.sub(r'\}','',text)
    text = re.sub(r'\\','',text)
    text = re.sub(r'\n{3,}','',text)
    text = text.strip()
    with open(os.path.join(outpath,os.path.splitext(os.path.basename(filename))[0]+'.txt3'),mode='w',encoding='utf-8') as fh:
        fh.write(text)
    if len(mathmatches)>0:
        print(filename, len(mathmatches))
    return len(mathmatches)

def main():
    global eqdict
    global outpath
    global inline
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("input_directory",help="directory of .tex files to overwrite")
    parser.add_argument("output_directory",help="directory to place output files")
    args = parser.parse_args()
    directory = args.input_directory
    outpath = args.output_directory
    filelist = gettexfiles(directory)
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    pool = mp.Pool(mp.cpu_count())
    vals = pool.map(cleanfile,filelist)
    print(sum(vals))
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
