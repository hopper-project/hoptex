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

def makeobjs(filename):
    '''
    Accepts filepath in filename, opens corresponding .tex and .xhtml files
    If the number of display mode math sections & math tables match up,
    generate a JSON object and write it out to the json path.
    '''
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
        # print("{}: missing converted file - {}".format(filename,convertedfilepath))
        # converteddoc = ""
        # eqs = []
        # xhtml_equations = []
        return ""
    else:
        with open(convertedfilepath,'r') as fh:
            converteddoc = fh.read()
        xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>',converteddoc)
    newtext = removecomments(text)
    docbody = re.findall(r'(?s)\\begin\{document\}(.*?)\\end\{document\}',newtext)
    if not docbody:
        print("{}: Missing body".format(filename))
        return "{}: Missing body".format(filename)
    docbody = docbody[0]
    #enforce that document body is in the document
    tex_equations = grabmath(newtext)
    if len(tex_equations)!=len(xhtml_equations):
        if len(xhtml_equations)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(tex_equations), len(xhtml_equations)))
            sanitizedfile = os.path.join(erroroutputpath,cleanname+'.tex')
            outstr = gensanitized(filename)
            if len(gensanitized(filename).strip())==0:
                print("{}: LaTeXML failure".format(filename))
                return("{}: LaTeXML failure".format(filename))
            else:
                with open(sanitizedfile,'w') as fh:
                    fh.write(gensanitized(filename))
        return "{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(tex_equations), len(xhtml_equations))
    else:
        for i, x in enumerate(xhtml_equations):
            tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
            if len(tempvar)==0:
                print("{}-{}: No math in table".format(filename, i))
                xhtml_equations[i] = ""
            else:
                xhtml_equations[i] =  tempvar
        split = grabmath(docbody,split=1)
        export_list = []
        for i, x in enumerate(tex_equations):
            try:
                index = split.index(x)
            except:
                print("{}: Equation matching failed".format(filename))
                return("{}: Equation matching failed".format(filename))
            nexttext = ""
            prevtext = ""
            # for y in range(i-1,-1,-1):
            #     if split[y] not in tex_equations:
            #         prevtext = split[y]
            #         break
            # for y in range(i+1,len(split)):
            #     if split[y] not in tex_equations:
            #         nexttext = split[y]
            #         break
            # if len(nexttext)>400:
            #     nexttext = nexttext[:400]
            # if len(prevtext)>400:
            #     prevtext = prevtext[-400:]
            if i in range(0, len(tex_equations)-1):
                if split[index-1] not in tex_equations:
                    prevtext = split[index-1]
                if split[index+1] not in tex_equations:
                    nexttext = split[index+1]
            location = docbody.find(x)
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=xhtml_equations[i])
            export_list.append(neweq)
            '''code for exporting each equation object as a JSON'''
            '''comment out the try/except statement in the outer loop
            if you want to use this'''
            # outfname = eqoutpath + cleanname + '.' + str(i) + '.json'
            # try:
            #     with open(outfname,'w') as fh:
            #         json.dump(neweq,fh,default=JSONHandler)
            # except:
            #     print("{}: Equation export to JSON failed".format(outfname))
            #     return("{}: Equation export to JSON failed".format(outfname))
        outfname = eqoutpath + cleanname + '.json'
        try:
            with open(outfname,'w') as fh:
                json.dump(export_list,fh,default=JSONHandler)
        except:
            print("{}: Equation export to JSON failed".format(outfname))
            return("{}: Equation export to JSON failed".format(outfname))

def main():
    global path
    global eqoutpath
    global convertedpath
    global erroroutputpath
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
    erroroutputpath = eqoutpath[:-1] + '_errors/'
    if not os.path.exists(eqoutpath):
        os.makedirs(eqoutpath)
    if not os.path.exists(erroroutputpath):
        os.makedirs(erroroutputpath)
    print("{}: Beginning processing".format(path))
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Finding all files with math...")
    filelist= getmathfiles(path)
    print("Generating equation object JSONs...")
    doclist = pool.map(makeobjs,filelist)
    print("JSON conversion complete")
    print("Logging...")
    with open(eqoutpath[:-1]+'.log','w') as fh:
        for x in doclist:
            if x:
                fh.write(x+'\n')
    print("Logging complete")
    print("{}: Finished".format(path))
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
