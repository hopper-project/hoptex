"""process_tsv
input: 4 column tsv, tex files
output: mml files, json files, xhtml files, 5 column tsv
"""

import sys #handling arguments passed to function
import glob #file path handling
import os #checking files and writing to/from files
import re
import multiprocessing as mp
import subprocess
import argparse
import time
import datetime
import queue
from subprocess import PIPE
from core.funcs import *
from core.texclasses import *
import json

global timeout
global erroroutputpath
global xhtml_path
global path
global eqoutpath


# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"

path = ''
xhtml_path = ''
erroroutputpath = ''
timeout = 1000
eqoutpath = ''


def writesanitized(sanitized, clean_file_name):
    """Writes sanitized document text to clean_file_name"""
    global erroroutputpath
    outfile = os.path.join(erroroutputpath, clean_file_name+'.tex')
    with open(outfile, 'w') as fh:
        fh.write(sanitized)

def generate_xhtml(filename):
    """Conversion function using subprocess: output is a an XML file and an XHTML file"""
    global xhtml_path
    global timeout

    clean_file_name = os.path.splitext(os.path.basename(filename))[0]
    outfname = os.path.join(xhtml_path, clean_file_name+'.xhtml')
    outrawname = os.path.join(xhtml_path, clean_file_name+'.txt')

    if os.path.isfile(outfname):
        # print("{}: Already generated".format(filename))
        return ""
    # print("{}: Start".format(filename))
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    output = generate_sanitized_document(text)
    if len(output) == 0:
        print("{}: Error - no body found".format(filename))
        return "{}: Error - no body found".format(filename)
    try:
        proc = subprocess.Popen(["latexml", "-"], stderr=PIPE, stdout=PIPE,
        stdin=PIPE)
        stdout, stderr = proc.communicate(output.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML conversion failed - timeout".format(filename))
        writesanitized(output,clean_file_name)
        return "{}: MathML conversion failed - timeout".format(filename)
    except:
        print("{}: Conversion failed".format(filename))
        writesanitized(output,clean_file_name)
        return "{}: Conversion failed".format(filename)
    try:
        proc = subprocess.Popen(["latexmlpost", "--format=xhtml", "-"],
        stderr=PIPE, stdout=PIPE, stdin=PIPE)
        stdout2, stderr = proc.communicate(stdout, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML postprocessing failed - timeout".format(filename))
        writesanitized(output,clean_file_name)
        return "{}: MathML postprocessing failed - timeout".format(filename)
    if len(stdout2.strip())==0:
        print("{}: Conversion failed".format(filename))
        writesanitized(output,clean_file_name)
        return "{}: Conversion failed".format(filename)
    stdout2 = stdout2.decode()
    stdout2 = re.sub(r'(href\=\").*?(LaTeXML\.css)(\")',r'\1\2\3',stdout2)
    stdout2 = re.sub(r'(href=\").*?(ltx-article\.css)(\")',r'\1\2\3',stdout2)

    generatetxt = True
    if(generatetxt):
        with open(outrawname,'w') as fh:
            try:
                fh.write(stdout.decode())
                #fh.write(stdout.decode('latin-1'))
            except:
                pass
    with open(outfname,'w') as fh:
        fh.write(stdout2)
    return ""

def generate_mathml(work_dir,tsv_file,out_dir):
    global xhtml_path
    tsv_dict = {}
    tex_dict = {}
    mml_dict = {}
    shouldAppend = False

    ## loading eqid and latex into dictionary
    print("Loading TSV...")
    with open(tsv_file,mode='r',encoding='utf-8') as fh:
        print("Creating dictionary of EQID and LaTeX...")
        line_count = 0
        for line in fh:
            line_count += 1
            line = line.strip()
            linesplit = line.split('\t')
            if len(linesplit)==4:
                eqid, eqtext, freq, _ = linesplit
            elif len(linesplit)==5:
                eqid, eqtext, mml, freq, _ = linesplit
            beqtext = unmask(eqtext)
            tsv_dict[eqid] = beqtext

    print("Creating dictionary of MathML and LaTeX...")
    for filename in work_dir:
        f1 = open(filename, mode='r',encoding='latin-1')
        text = f1.read()
        f1.close()
        clean_name = os.path.basename(os.path.splitext(filename)[0])
        convertedfilepath = os.path.join(xhtml_path,clean_name+'.xhtml')
        if not os.path.isfile(convertedfilepath):
            print("{}: missing converted file - {}".format(filename,convertedfilepath))
            # converted_document = ""
            # eqs = []
            # xhtml_equations = []
            return ""
        else:
            with open(convertedfilepath,'r') as fh:
                converted_document = fh.read()
                #print(converted_document)
                #print("----------------------------------------------------------")
            xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>',converted_document)
        document_body = grab_body(text)
        if not document_body:
            print("{}: Missing body".format(filename))
            return "{}: Missing body".format(filename)
        tex_equations = grab_math(text)

        #print(len(xhtml_equations))
        #print(len(tex_equations))
        #print(tex_equations)
        ## compare tex and xhtml equations
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
            print(type(xhtml_equations))
            mml_queue = queue.Queue()
            for i, x in enumerate(xhtml_equations):
                tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>',x))
                if len(tempvar)==0:
                    print("{}-{}: No math in table".format(filename, i))
                    xhtml_equations[i] = ""
                else:
                    xhtml_equations[i] =  tempvar
                    eq_mml = x
                    mml_queue.put(eq_mml) ## EQ MathML
            split = grab_math(text,split=1)
            export_list = []
            for i, x in enumerate(tex_equations):
                try:
                    index = split.index(x)
                    eq_latex = standardize_equation(x)
                    eq_latex = beq + eq_latex + eeq
                    tex_dict[mml_queue.get()] = eq_latex
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
                print('Creating JSON files...')
                with open(outfname,'w') as fh:
                    json.dump(export_list,fh,default=JSONHandler)
                print('JSON files created!')
            except:
                print("{}: Equation export to JSON failed".format(outfname))



    ## if latex match then attach mml to EQID
    print("Attaching EQID to MathML...")
    for eqid, eqtext in tsv_dict.items():
        for mml, eqtext2 in tex_dict.items():
            if(eqtext == eqtext2):
                #print(eqid)
                mml_dict[eqid] = mml
                
    #print(tsv_dict.items())
    #for mml, eqtext2 in tex_dict.items():
    #    if "dagger" in eqtext2:
    #        print(eqtext2)

    ## write mml to tsv
    print("Writing MathML to TSV file...")
    output_file = tsv_file+'.mathml' ## new tsv created
    outfile = open(output_file,mode='w')
    line_count = 0
    with open(tsv_file,mode='r',encoding='utf-8') as fg:
        for line in fg:
            line = line.strip()
            linesplit = line.split('\t')
            if len(linesplit)==4:
                eqid, eqtext, freq, _ = linesplit
            elif len(linesplit)==5:
                eqid, eqtext, mml, freq, _ = linesplit
            if "IX" in eqid:
                continue
            line_count += 1
            mathmlrep = mml_dict[eqid]
            ## creating mml files
            mathml_eq_file = open(os.path.join(out_dir,eqid.lower()+".mml"),'w')
            mathml_eq_file.write(mathmlrep) ##
            mathml_eq_file.close()
            ## writing mml to tsv file
            mathmlrep = mask("\"" + mathmlrep + "\"")
            outfile.write("\t".join(linesplit[0:-2])+"\t"+mathmlrep+"\t"+linesplit[-2]+"\t"+linesplit[-1]+"\n")
            if (line_count%1000==0):
                print(line_count)
    outfile.close()
    print("Loaded {} equations".format(line_count))
    outlist = []
    return(outlist)


def main():
    tsv_file = ''
    mml_path = ''
    start_time = time.time()
    parser = argparse.ArgumentParser(description='Conversion of sanitized LaTeX documents to XHTML')
    parser.add_argument("tex_dir",help="Path to input directory of .tex files")
    parser.add_argument("xhtml_dir",help="Path to output directory for .xhtml files")
    parser.add_argument("--tsv_file",help="Input .tsv file for mml generation")
    parser.add_argument("--mml_dir",help="Path to output directory for .mml files")
    parser.add_argument("--json_dir",help="Path to output directory for .json files")
    parser.add_argument("--timeout",help="Specify custom timeout")
    args = parser.parse_args()
    origdir = os.getcwd()
    path = os.path.abspath(args.tex_dir)
    xhtml_path = os.path.abspath(args.xhtml_dir)
    tsv_path = os.path.abspath(args.tsv_file)
    mml_path = os.path.abspath(args.mml_dir)
    eqoutpath = os.path.abspath(args.json_dir)

    if not os.path.isdir(path):
        print("Error: {} is not a valid directory".format(path))
        sys.exit()
    if args.timeout:
        timeout = int(args.timeout)
        print("New timeout: {}s".format(timeout))

    xhtml_path = os.path.join(os.path.abspath(xhtml_path),'')
    validate_folder(xhtml_path)
    os.chdir(xhtml_path)
    erroroutputpath = os.path.join(os.path.split(os.path.normpath(xhtml_path))[0],
    os.path.basename(os.path.normpath(path))+'_failed')
    validate_folder(erroroutputpath)

    print("Beginning processing of {}".format(path))
    print("Generating list of files with math...")
    filelist = getmathfiles(path) 
    print("Generation complete.")
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Beginning processing...")
    outlist = pool.map(generate_xhtml,filelist)
    print(outlist)

    tsv = True
    if(tsv):
        print('Generating MathML representation...')
        generate_mathml(filelist,tsv_path,mml_path)

    with open(xhtml_path[:-1]+".log",'w') as fh:
        for message in outlist:
            if len(message)>0:
                fh.write(message+'\n')
        end_time = time.time()
        total_time = str(datetime.timedelta(seconds=int(end_time-start_time)))
        fh.write("TIME (hh:mm:ss): {}\n".format(total_time))
    pool.close()
    pool.join()
    os.chdir(origdir)
    print("TIME: {}".format(total_time))


if __name__ == '__main__':
    main()
