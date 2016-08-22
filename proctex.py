#!/usr/bin/env python
#proctex.py - generates equation & document objects
#Jay Dhanoa
#before running this script, run getarxivdatav2.py for the corresponding folder
import sys #handling arguments passed to function
import glob #file path handling
import os #checking files and writing to/from files
import re #regex matching
import multiprocessing as mp #drastic speedups when implemented on an i7-4710HQ
import heapq #to find n largest elements in makegraph
import pickle #serializing to/from disk
import subprocess
from subprocess import PIPE
import json
from core.texclasses import *
from core.funcs import *
path = ''
outpath = ''
eqoutpath = ''
#FUNCTIONS

#split on period function for multithreaded mapping
def proc(instr):
    val = instr.split()
    val[1] = (val[1].split('.'))[0]
    return val


def makeobjs(filename):
    global outpath
    global eqoutpath
    global convertedpath
    global erroroutputpath
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
        tableeqs = []
    else:
        with open(convertedfilepath,'r') as fh:
            converteddoc = fh.read()
        tableeqs = re.findall(r'(?s)\<table.*?\<\/table\>',converteddoc)
    newtext = removecomments(text)
    docbody = re.findall(r'(?s)\\begin\{document\}(.*?)\\end\{document\}',newtext)
    if not docbody:
        print("{}: Missing body".format(filename))
        return
    docbody = docbody[0]
    actualeqs = grabmath(newtext)
    if len(actualeqs)!=len(tableeqs):
        if len(tableeqs)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(actualeqs), len(tableeqs)))
            sanitizedfile = os.path.join(erroroutputpath,cleanname+'.tex')
            # with open(sanitizedfile,'w') as fh:
            #     fh.write(genxhtml(filename))
        #print("{}: skipping...".format(filename))
        return
    else:
        for i, x in enumerate(tableeqs):
            tableeqs[i] = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
        split = grabmath(docbody,split=1)
        for i, x in enumerate(actualeqs):
            index = split.index(x)
            nexttext = ""
            prevtext = ""
            for y in range(i-1,-1,-1):
                if isinstance(split[y],str):
                    prevtext = split[y]
                    break
            for y in range(i+1,len(split)):
                if isinstance(split[y],str):
                    nexttext = split[y]
                    break
            if len(nexttext)>400:
                nexttext = nexttext[:400]
            if len(prevtext)>400:
                prevtext = prevtext[-400:]
            location = docbody.find(x)
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=tableeqs[i])
            outfname = eqoutpath + cleanname + '.' + str(i) + '.json'
            try:
                with open(outfname,'w') as fh:
                    json.dump(neweq,fh,default=JSONHandler)
            except:
                print("{}: Equation export to JSON failed".format(outfname))

def main():
    global path
    global outpath
    global eqoutpath
    global convertedpath
    global erroroutputpath
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
    erroroutputpath = path[:-1] + '_errors/'
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    if not os.path.exists(eqoutpath):
        os.makedirs(eqoutpath)
    if not os.path.exists(erroroutputpath):
        os.makedirs(erroroutputpath)
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
    #filelist = ['/home/jay/hopper/hoptex/1501/1501.04805.tex']
    #filedictlist is the result of makedict mapped over each filename
    #filelist[0] corresponds to filedictlist[0]
    doclist = pool.map(makeobjs,filelist)
    print("Object generation complete")
    #handles closing of multiple processes
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
