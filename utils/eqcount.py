#!/usr/bin/env python
#parsetex.py
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

#split on period function for multithreaded mapping
def proc(instr):
    val = instr.split()
    val[1] = (val[1].split('.'))[0]
    return val

#makes a dictionary of counted values
def makedict(filename):
    with open(filename, mode='r', encoding='latin-1') as fh:
        text = fh.read()
    #remove comments
    text = re.sub(r'(?m)^%+.*$','',text) #remove all comments at beginning of lines
    text = re.sub(r"(?m)([^\\])\%+.*?$",r'\1',text) #remove all remaining comments
    text = re.sub(r'\\begin\{comment\}.*?\\end\{comment\}','',text,re.DOTALL)
    #series of regex expressions
    a = re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',text,re.DOTALL)
    b = re.findall(r'\\begin\{multline\}(.*?)\\end\{multline\}',text,re.DOTALL)
    c = re.findall(r'\\begin\{gather\}(.*?)\\end\{gather\}',text,re.DOTALL)
    d = re.findall(r'\\begin\{align\}(.*?)\\end\{align\}',text,re.DOTALL)
    e = re.findall(r'\\begin\{flalign\*\}(.*?)\\end\{flalign\*\}',text,re.DOTALL)
    f = re.findall(r'\\begin\{math\}(.*?)\\end\{math\}',text,re.DOTALL)
    g = re.findall(r'[^\\]\\\[(.*?)\\\]',text,re.DOTALL)
    h = re.findall(r'\$\$([^\^].*?)\$\$',text,re.DOTALL)
    l = re.findall(r'[^\\]\$(.*?)\$',text,re.DOTALL)
    m = re.findall(r'\\\((.*?)\\\)',text,re.DOTALL)
    finds = a + b + c + d + e + f + g + h + l + m
    if len(finds)==0:
        if "\\begin{document}" in text:
            print(filename)
    return len(finds)

def main():
    #default path to directory with tex files
    path = '1506/'
    #The program accepts a directory to be analyzed
    #The directory should have the LaTeX files (entered without the '/')
    if(len(sys.argv)>2):
        path = str(sys.argv[1]+'/')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a directory")
            sys.exit()
    #per getarxivdatav2, the metadata for tex files in a folder
    #should be in a .txt file of the same name
    metadata = path[:-1] + '.txt'
    #read in data
    #remove general subcategories
    #initialize number of threads to the number of cpu cores
    pool = mp.Pool(processes=mp.cpu_count())
    #error handling for missing metadata file
    if not os.path.isfile(metadata):
        print("Error: file not found. Make sure you've entered the correct directory AND have run getarxivdatav2.py for said directory.")
        sys.exit()
    #load in the list of files and their categories
    filecats = open(metadata,'r')
    lines = filecats.readlines()
    print("Read in file metadata.")
    #each line of the form 'filename.tex' 'category'
    #this changes it to just 'filename' and 'category'
    #lines = pool.map(proc,lines)
    lines = pool.map(proc,lines)
    #dictionary of categories
    #keys are category names
    #values are count dictionaries of tokens in papers of the category
    categories = {}
    #dictionary of filenames and their associated categories
    fnamedict = {}

    #populate the respective dictionaries
    for x in lines:
        if x[1] not in categories:
            categories[x[1]] = {}
        fnamedict[x[0]] = x[1]
    print("Populated dictionaries.")
    #list of tex files in the directory specified by path
    filelist= glob.glob(os.path.join(path,'*.tex'))
    if len(lines)!=len(filelist):
        print("Warning: possible mismatch - the number of .tex files has changed since metadata was last generated. Rerun getarxivdatav2.py to update metadata")
    print("Getting token counts of files...")
    #filedictlist is the result of makedict mapped over each filename
    #filelist[0] corresponds to filedictlist[0]
    #filedictlist = pool.map(makedict,filelist)
    filedictlist = pool.map(makedict,filelist)
    noeqs = 0
    haseqs = 0
    toteqs = 0
    for x in filedictlist:
        if x==0:
            noeqs+=1
        else:
            haseqs += 1
            toteqs += x
    print(noeqs)
    print(haseqs)
    print(float(toteqs)/haseqs)
    print(toteqs)
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
