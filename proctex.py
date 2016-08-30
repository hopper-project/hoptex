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
        return("{}: Missing XHTML".format(filename))
    else:
        with open(convertedfilepath,'r') as fh:
            converteddoc = fh.read()
        tableeqs = re.findall(r'(?s)\<table.*?\<\/table\>',converteddoc)
    newtext = removecomments(text)
    docbody = re.findall(r'(?s)\\begin\{document\}(.*?)\\end\{document\}',newtext)
    if not docbody:
        print("{}: Missing body".format(filename))
        return("{}: Missing body".format(filename))
    docbody = docbody[0]
    actualeqs = grabmath(newtext)
    if len(actualeqs)!=len(tableeqs):
        if len(tableeqs)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(actualeqs), len(tableeqs)))
            sanitizedfile = os.path.join(erroroutputpath,cleanname+'.tex')
            with open(sanitizedfile,'w') as fh:
                fh.write(genxhtml(filename))
        #print("{}: skipping...".format(filename))
        return "{}: LaTeX/XHTML equation count mismatch {} {}"
    else:
        for i, x in enumerate(tableeqs):
            tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
            if len(tempvar)==0:
                print("{}-{}: No math in table".format(filename, i))
                return "{}-{}: No math in table".format(filename, i)
            else:
                tableeqs[i] =  tempvar
        split = grabmath(docbody,split=1)
        for i, x in enumerate(actualeqs):
            outfname = eqoutpath + cleanname + '.' + str(i) + '.json'
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
            if len(tableeqs[i].strip())==0:
                print("{}: Empty JSON {} \"{}\" - \n{}".format(filename,type(tableeqs[i]),tableeqs[i],tempvar))
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=tableeqs[i])

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
    if(len(sys.argv)==3):
        path = os.path.join(str(sys.argv[1]),'')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a valid directory")
            sys.exit()
        eqoutpath=os.path.join(str(sys.argv[2]),'')
    else:
        print("Error: incorrect number of arguments")
        print("Usage: python3 proctex.py /folder/to/tex/files/ /folder/to/output/")
        sys.exit()
    eqoutpath = path
    erroroutputpath = path[:-1] + '_errors/'
    if not os.path.exists(eqoutpath):
        os.makedirs(eqoutpath)
    if not os.path.exists(erroroutputpath):
        os.makedirs(erroroutputpath)
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    filelist= getmathfiles(path)
    doclist = pool.map(makeobjs,filelist)
    print("Object generation complete")
    #handles closing of multiple processes
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
