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
import cPickle #serializing to/from disk
from nltk.tokenize import word_tokenize, sent_tokenize
import gc
import subprocess
from subprocess import PIPE
import json
from core.texclasses import *
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
    #print("Start: {}".format(filename))
    f1 = open(filename, 'rt')
    text = f1.read()
    f1.close()
    newtext = text.decode('utf-8', 'ignore')
    #remove comments
    #remove all comments at beginning of lines
    newtext = re.sub(r'(?m)^%+.*$', '', newtext)
    #remove all remaining comments
    cdelim = " CUSTOMDELIMITERHERE "
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
    map(strip,dispeqs)
    textlist = newtext.split(cdelim)
    textlist = map(strip,textlist)
    for i in range(len(textlist)):
        if textlist[i] in dispeqs:
            textlist[i] = equation(eqtext = textlist[i], fname = filename)
    newdoc = document(filename,textlist)
    outfname = outpath + (newdoc.name.split('/')[-1])[:-4]+'.pkl'
    with open(outfname,'w') as fh:
        try:
            cPickle.dump(newdoc,fh)
        except:
            print("{}: Export to pkl failed".format(outfname))
    outfname = outpath + (newdoc.name.split('/')[-1])[:-4]+'.json'
    try:
        with open(outfname,'w') as fh:
            json.dump(newdoc,fh,default=JSONHandler)
    except:
        print("{}: Export to JSON failed".format(outfname))
    #print("Finish: {}".format(filename))
    eqlist = newdoc.get_equations()
    for i, eq in enumerate(eqlist):
        outfname = eqoutpath + (newdoc.name.split('/')[-1])[:-4]+'.'+str(i)+'.json'
        try:
            with open(outfname,'w') as fh:
                json.dump(eq,fh,default=JSONHandler)
        except:
            print("{}: Equation export to JSON failed".format(outfname))
    return newdoc

def main():
    global path
    global outpath
    global eqoutpath
    #default path to directory with tex files
    path = '1506/'
    #The program accepts a directory to be analyzed
    #The directory should have the LaTeX files (entered without the '/')
    if(len(sys.argv)>2):
        path = os.path.join(str(sys.argv[1]),'')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a valid directory")
            sys.exit()
    #per getarxivdatav2, the metadata for tex files in a folder
    #should be in a .txt file of the same name
    metadata = path[:-1] + '.txt'
    outpath = path[:-1] + '_documents/'
    eqoutpath = path[:-1] + '_equations/'
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
    if not os.path.isfile(metadata):
        print("Error: file not found. Make sure you've entered the correct directory AND have run getarxivdatav2.py for said directory.")
        sys.exit()
    #load in the list of files and their categories
    filecats = open(metadata,'r')
    lines = filecats.readlines()
    filecats.close()
    print("Read in file metadata.")
    #each line of the form 'filename.tex' 'category'
    #this changes it to just 'filename' and 'category'
    lines = pool.map(proc,lines)
    #dictionary of categories
    #keys are category names
    #values are count dictionaries of tokens in papers of the category
    categories = {}
    #dictionary of file names and their associated categories
    fnamedict = {}
    for x in lines:
        if x[1] not in categories:
            categories[x[1]] = {}
        fnamedict[x[0]] = x[1]
    print("Populated file category dictionary.")
    #list of tex files in the directory specified by path
    filelist= glob.glob(os.path.join(path,'*.tex'))
    if len(lines)!=len(filelist):
        print("Warning: possible mismatch - the number of .tex files has changed since metadata was last generated. Rerun getarxivdatav2.py to update metadata")
    print("Generating doc/equation objects...")
    #filedictlist is the result of makedict mapped over each filename
    #filelist[0] corresponds to filedictlist[0]
    doclist = pool.map(makeobjs,filelist)
    print("Object generation complete")
    #handles closing of multiple processes
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
