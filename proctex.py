#!/usr/bin/env python
#proctex.py - generates equation & document objects
#Jay Dhanoa
import sys #handling arguments passed to function
import glob #file path handling
import os #checking files and writing to/from files
import re #regex matching
import multiprocessing as mp #drastic speedups when implemented on an i7-4710HQ
import heapq #to find n largest elements in makegraph
import pickle #serializing to/from disk
import subprocess
import argparse
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
    f1 = open(filename, mode='r', encoding='latin-1')
    text = f1.read()
    f1.close()
    clean_name = os.path.basename(os.path.splitext(filename)[0])
    convertedfilepath = os.path.join(convertedpath,clean_name+'.xhtml')
    if not os.path.isfile(convertedfilepath):
        print("{}: missing converted file - {}".format(filename,convertedfilepath))
        # converted_document = ""
        # eqs = []
        # xhtml_equations = []
        return ""
    else:
        with open(convertedfilepath,'r') as fh:
            converted_document = fh.read()
        xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>',converted_document)
    document_body = grab_body(text)
    if not document_body:
        print("{}: Missing body".format(filename))
        return "{}: Missing body".format(filename)
    tex_equations = grab_math(text)
    if len(tex_equations)!=len(xhtml_equations):
        if len(xhtml_equations)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(tex_equations), len(xhtml_equations)))
            sanitizedfile = os.path.join(erroroutputpath,clean_name+'.tex')
            outstr = generate_sanitized_document(filename)
            print("Attempting to sanitize: {}".format(filename))
            if len(outstr.strip())==0:
                print("{}: LaTeXML failure".format(filename))
                return("{}: LaTeXML failure".format(filename))
            else:
                with open(sanitizedfile,'w') as fh:
                    fh.write(generate_sanitized_document(filename))
        return "{}: LaTeX/XHTML equation count mismatch: LaTeX - {}, XHTML - {}".format(filename, len(tex_equations), len(xhtml_equations))
    else:
        for i, x in enumerate(xhtml_equations):
            tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
            if len(tempvar)==0:
                print("{}-{}: No math in table".format(filename, i))
                xhtml_equations[i] = ""
            else:
                xhtml_equations[i] =  tempvar
        split = grab_math(text,split=1)
        export_list = []
        for i, x in enumerate(tex_equations):
            try:
                index = split.index(x)
            except:
                print("{}: Equation matching failed".format(filename))
                return("{}: Equation matching failed".format(filename))
            nexttext = ""
            prevtext = ""
            if i in range(0, len(tex_equations)):
                if split[index-1] not in tex_equations:
                    prevtext = split[index-1]
                if split[index+1] not in tex_equations:
                    nexttext = split[index+1]
            location = document_body.find(x)
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=xhtml_equations[i])
            export_list.append(neweq)
        outfname = os.path.join(eqoutpath,clean_name + '.json')
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
    parser = argparse.ArgumentParser(description='Usage for JSON object generation')
    parser.add_argument("tex_directory", help="Path to directory of .tex files")
    parser.add_argument("xhtml_directory", help="Path to directory of .tex files")
    parser.add_argument("output_dir", help="Path to output directory")
    args = parser.parse_args()
    path = os.path.abspath(args.tex_directory)
    convertedpath = os.path.abspath(args.xhtml_directory)
    eqoutpath = os.path.abspath(args.output_dir)
    erroroutputpath = os.path.normpath(eqoutpath) + '_errors/'
    validate_folder(eqoutpath)
    validate_folder(convertedpath)
    validate_folder(erroroutputpath)
    print("{}: Beginning processing".format(path))
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Finding all files with math...")
    filelist= getmathfiles(path)
    print("Generating equation object JSONs...")
    errormessages = pool.map(makeobjs,filelist)
    print("JSON conversion complete")
    print("Logging...")
    with open(os.path.normpath(eqoutpath)+'.log','w') as fh:
        for message in errormessages:
            if message:
                fh.write(message+'\n')
    print("Logging complete: {}".format(os.path.normpath(eqoutpath)+'.log'))
    print("{}: Finished".format(path))
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
