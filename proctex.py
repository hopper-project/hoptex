#!/usr/bin/env python
#proctex.py - generates equation & document objects
#Jay Dhanoa
#before running this script, run getarxivdatav2.py for the corresponding folder
import sys #handling arguments passed to function
import glob #file path handling
import os #checking files and writing to/from files
import re #regex matching
import numpy as np #for use in pyplot
import matplotlib.pyplot as pl #used to plot graphs
import multiprocessing as mp #drastic speedups when implemented on an i7-4710HQ
import heapq #to find n largest elements in makegraph
import pickle #serializing to/from disk
from nltk.tokenize import word_tokenize, sent_tokenize
import gc
import subprocess
from subprocess import PIPE
import json
from core.texclasses import *
from core.funcs import *
path = ''
outpath = ''
eqoutpath = ''
#FUNCTIONS

def strip(param):
    return param.strip()

#split on period function for multithreaded mapping
def proc(instr):
    val = instr.split()
    val[1] = (val[1].split('.'))[0]
    return val

def makeobjs(filename):
    global outpath
    global eqoutpath
    global convertedpath
    #print("Start: {}".format(filename))
    f1 = open(filename, mode='r', encoding='latin-1')
    text = f1.read()
    f1.close()
    cleanname = os.path.basename(os.path.splitext(filename)[0])
    convertedfilepath = os.path.join(convertedpath,cleanname+'.xhtml')
    if not os.path.isfile(convertedfilepath):
        #print("{}: missing converted file - {}".format(filename,convertedfilepath))
        converteddoc = ""
        eqs = []
    else:
        with open(convertedfilepath,'r') as fh:
            converteddoc = fh.read()
        eqs = re.findall(r'\<math.*?\<\/math>',converteddoc)
    newtext = text
    #remove comments
    #remove all comments at beginning of lines
    newtext = re.sub(r'(?m)^%+.*$', '', newtext)
    #remove all remaining comments
    cdelim = "CUSTOMDELIMITERHERE"
    newtext = re.sub(r"(?m)([^\\])\%+.*?$", r'\1', newtext)
    newtext = re.sub(r'\\begin\{comment\}.*?\\end\{comment\}','',newtext,re.DOTALL)
    newtext = re.sub(r'(?s)\\begin\{equation\}(.*?)\\end\{equation\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\\begin\{multline\}(.*?)\\end\{multline\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\\begin\{gather\}(.*?)\\end\{gather\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\\begin\{align\}(.*?)\\end\{align\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\\begin\{flalign\*\}(.*?)\\end\{flalign\*\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\\begin\{math\}(.*?)\\end\{math\}',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)[^\\]\\\[(.*?)\\\]',cdelim + r'\1' + cdelim,newtext)
    newtext = re.sub(r'(?s)\$\$([^\^].*?)\$\$',cdelim + r'\1' + cdelim,newtext)
    dispeqs = re.findall(r'(?s)' + cdelim + r'(.*?)' + cdelim,newtext)
    actualeqs  = re.findall(r'(?s)\\begin\{equation\}.*?\\end\{equation\}|\\begin\{multline\}.*?\\end\{multline\}|\\begin\{gather\}.*?\\end\{gather\}|\\begin\{align\}.*?\\end\{align\}|\\begin\{flalign\*\}.*?\\end\{flalign\*\}|\\begin\{math\}.*?\\end\{math\}|[^\\]\\\[.*?\\\]|\$\$[^\^].*?\$\$',text)
    map(strip,dispeqs)
    textlist = newtext.split(cdelim)
    if len(dispeqs)!=len(eqs):
        if len(eqs)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {} {}".format(filename, len(dispeqs), len(eqs), len(actualeqs)))
    textlist = list(map(strip,textlist))
    for i in range(len(textlist)):
        if textlist[i] in dispeqs:
            textlist[i] = equation(eqtext = textlist[i], fname = filename)
    #newdoc = document(filename,textlist)
    # outfname = outpath + (newdoc.name.split('/')[-1])[:-4]+'.json'
    # try:
    #     with open(outfname,'w') as fh:
    #         json.dump(newdoc,fh,default=JSONHandler)
    # except:
    #     print("{}: Export to JSON failed".format(outfname))
    #print("Finish: {}".format(filename))
    # eqlist = newdoc.get_equations()
    # for i, eq in enumerate(eqlist):
    #     outfname = eqoutpath + cleanname+'.'+str(i)+'.json'
    #     if(eqs):
    #         eq.mathml = eqs[i]
    #     try:
    #         with open(outfname,'w') as fh:
    #             json.dump(eq,fh,default=JSONHandler)
    #     except:
    #         print("{}: Equation export to JSON failed".format(outfname))
    # return newdoc

def main():
    global path
    global outpath
    global eqoutpath
    global convertedpath
    #default path to directory with tex files
    path = 'demacro/'
    #The program accepts a directory to be analyzed
    #The directory should have the LaTeX files (entered without the '/')
    if(len(sys.argv)>1):
        path = os.path.join(str(sys.argv[1]),'')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a valid directory")
            sys.exit()
    #per getarxivdatav2, the metadata for tex files in a folder
    #should be in a .txt file of the same name
    outpath = path[:-1] + '_documents/'
    eqoutpath = path[:-1] + '_equations/'
    convertedpath = path[:-1] + '_converted/'
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    if not os.path.exists(eqoutpath):
        os.makedirs(eqoutpath)
    #read in data
    #remove general subcategories
    #initialize number of threads to the number of cpu cores
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    #error handling for missing metadata file
    #load in the list of files and their categories
    #each line of the form 'filename.tex' 'category'
    #this changes it to just 'filename' and 'category'
    #list of tex files in the directory specified by path
    filelist= getmathfiles(path)
    #filedictlist is the result of makedict mapped over each filename
    #filelist[0] corresponds to filedictlist[0]
    doclist = pool.map(makeobjs,filelist)
    print("Object generation complete")
    #handles closing of multiple processes
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
