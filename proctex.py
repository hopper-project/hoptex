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
eqoutpath = ''
#FUNCTIONS

#split on period function for multithreaded mapping
def proc(instr):
    val = instr.split()
    val[1] = (val[1].split('.'))[0]
    return val


def makeobjs(filename):
    global eqoutpath
    global convertedpath
    global erroroutputpath
    global missingoutputpath
    #print("Start: {}".format(filename))
    f1 = open(filename, mode='r', encoding='latin-1')
    text = f1.read()
    f1.close()
    cleanname = os.path.basename(os.path.splitext(filename)[0])
    convertedfilepath = os.path.join(convertedpath,cleanname+'.xhtml')
    if not os.path.isfile(convertedfilepath):
        print("{}: missing converted file - {}".format(filename,convertedfilepath))
        # converteddoc = ""
        # eqs = []
        # tableeqs = []
        sanitizedfile = os.path.join(missingoutputpath,cleanname+'.tex')
        outstr = gensanitized(filename)
        if len(outstr.strip())==0:
            return
        else:
            with open(sanitizedfile,'w') as fh:
                fh.write(gensanitized(filename))
        return "{}: missing converted file - {}".format(filename,convertedfilepath)
    else:
        with open(convertedfilepath,'r') as fh:
            converteddoc = fh.read()
        tableeqs = re.findall(r'(?s)\<table.*?\<\/table\>',converteddoc)
    newtext = removecomments(text)
    docbody = re.findall(r'(?s)\\begin\{document\}(.*?)\\end\{document\}',newtext)
    if not docbody:
        print("{}: Missing body".format(filename))
        return "{}: Missing body".format(filename)
    docbody = docbody[0]
    actualeqs = grabmath(newtext)
    if len(actualeqs)!=len(tableeqs):
        if len(tableeqs)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(actualeqs), len(tableeqs)))
            sanitizedfile = os.path.join(erroroutputpath,cleanname+'.tex')
            outstr = gensanitized(filename)
            if len(outstr.strip())==0:
                return
            else:
                with open(sanitizedfile,'w') as fh:
                    fh.write(gensanitized(filename))
        return "{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(actualeqs), len(tableeqs))
    else:
        for i, x in enumerate(tableeqs):
            tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
            if len(tempvar)==0:
                print("{}-{}: No math in table".format(filename, i))
                tableeqs[i] = ""
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
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=tableeqs[i])
            try:
                with open(outfname,'w') as fh:
                    json.dump(neweq,fh,default=JSONHandler)
            except:
                print("{}: Equation export to JSON failed".format(outfname))

def main():
    global path
    global eqoutpath
    global convertedpath
    global erroroutputpath
    global missingoutputpath
    if(len(sys.argv)==4):
        path = os.path.join(str(sys.argv[1]),'')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a valid directory")
            sys.exit()
        convertedpath = os.path.join(str(sys.argv[2]),'')
        eqoutpath = os.path.join(str(sys.argv[3]),'')
    else:
        print("Error: usage")
        sys.exit()
    #per getarxivdatav2, the metadata for tex files in a folder
    #should be in a .txt file of the same name
    erroroutputpath = eqoutpath[:-1] + '_errors/'
    missingoutputpath = eqoutpath[:-1] + '_missing/'
    if not os.path.exists(eqoutpath):
        os.makedirs(eqoutpath)
    if not os.path.exists(erroroutputpath):
        os.makedirs(erroroutputpath)
    if not os.path.exists(missingoutputpath):
        os.makedirs(missingoutputpath)
    print("{}: Beginning processing")
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    filelist= getmathfiles(path)
    doclist = pool.map(makeobjs,filelist)
    print("JSON conversion complete")
    print("Logging...")
    with open(eqoutpath[:-1]+'.log','w') as fh:
        for x in doclist:
            if x:
                fh.write(x+'\n')
    print("Loggin complete")
    #handles closing of multiple processes
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
