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
    clean_name = os.path.basename(os.path.splitext(filename)[0])
    convertedfilepath = os.path.join(convertedpath,clean_name+'.xhtml')
    if not os.path.isfile(convertedfilepath):
        # print("{}: missing converted file - {}".format(filename,convertedfilepath))
        # converted_document = ""
        # eqs = []
        # xhtml_equations = []
        return ""
    else:
        with open(convertedfilepath,'r') as fh:
            converted_document = fh.read()
        xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>',converted_document)
    newtext = remove_comments(text)
    document_body = re.findall(r'(?s)\\begin\{document\}(.*?)\\end\{document\}',newtext)
    if not document_body:
        print("{}: Missing body".format(filename))
        return "{}: Missing body".format(filename)
    document_body = document_body[0]
    #enforce that document body is in the document
    tex_equations = grab_math(newtext)
    if len(tex_equations)!=len(xhtml_equations):
        if len(xhtml_equations)!=0:
            print("{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(tex_equations), len(xhtml_equations)))
            sanitizedfile = os.path.join(erroroutputpath,clean_name+'.tex')
            outstr = generate_sanitized_document(filename)
            if len(generate_sanitized_document(filename).strip())==0:
                print("{}: LaTeXML failure".format(filename))
                return("{}: LaTeXML failure".format(filename))
            else:
                with open(sanitizedfile,'w') as fh:
                    fh.write(generate_sanitized_document(filename))
        return "{}: LaTeX/XHTML equation count mismatch {} {}".format(filename, len(tex_equations), len(xhtml_equations))
    else:
        for i, x in enumerate(xhtml_equations):
            tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
            if len(tempvar)==0:
                print("{}-{}: No math in table".format(filename, i))
                xhtml_equations[i] = ""
            else:
                xhtml_equations[i] =  tempvar
        split = grab_math(document_body,split=1)
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
            if i in range(0, len(tex_equations)):
                if split[index-1] not in tex_equations:
                    prevtext = split[index-1]
                if split[index+1] not in tex_equations:
                    nexttext = split[index+1]
            location = document_body.find(x)
            neweq = equation(eqtext=x,fname=os.path.basename(filename),pos=location,nexttext=nexttext,prevtext=prevtext,index=index,mathml=xhtml_equations[i])
            export_list.append(neweq)
            '''code for exporting each equation object as a JSON'''
            '''comment out the try/except statement in the outer loop
            if you want to use this'''
            # outfname = eqoutpath + clean_name + '.' + str(i) + '.json'
            # try:
            #     with open(outfname,'w') as fh:
            #         json.dump(neweq,fh,default=JSONHandler)
            # except:
            #     print("{}: Equation export to JSON failed".format(outfname))
            #     return("{}: Equation export to JSON failed".format(outfname))
        outfname = eqoutpath + clean_name + '.json'
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
    erroroutputpath = os.normpath(eqoutpath) + '_errors/'
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
