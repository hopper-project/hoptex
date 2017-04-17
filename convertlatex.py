"""Script for converting a folder of .tex documents to a folder of
.xhtml documents, using LaTeXML
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
from subprocess import PIPE
from core.funcs import *

global timeout
global erroroutputpath
global outpath

path = ''
outpath = ''
timeout = 240
def writesanitized(sanitized, clean_file_name):
    """Writes sanitized document text to clean_file_name"""
    global erroroutputpath
    outfile = os.path.join(erroroutputpath, clean_file_name+'.tex')
    with open(outfile, 'w') as fh:
        fh.write(sanitized)

def genxhtml(filename):
    """Conversion function using subprocess"""
    global outpath
    global timeout
    clean_file_name = os.path.splitext(os.path.basename(filename))[0]
    outfname = outpath + clean_file_name+'.xhtml'
    outrawname = output+clean_file_name+'.txt'
    outdir = outpath + clean_file_name
    validate_folder(outdir)
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
    # try:
    #     proc = subprocess.Popen(["latexmlpost", "--format=html5", "--destination="+os.path.join(outdir,clean_file_name)+".html", "--mathimages", "-"],
    #     stderr=PIPE, stdout=PIPE, stdin=PIPE)
    #     stdout3, stderr = proc.communicate(stdout, timeout=timeout)
    # except subprocess.TimeoutExpired:
    #     proc.kill()
    #     print("{}: MathML postprocessing failed - timeout".format(filename))
    #     writesanitized(output,clean_file_name)
    #     return "{}: MathML postprocessing failed - timeout".format(filename)
    if len(stdout2.strip())==0:
        print("{}: Conversion failed".format(filename))
        writesanitized(output,clean_file_name)
        return "{}: Conversion failed".format(filename)
    stdout2 = stdout2.decode()
    stdout2 = re.sub(r'(href\=\").*?(LaTeXML\.css)(\")',r'\1\2\3',stdout2)
    stdout2 = re.sub(r'(href=\").*?(ltx-article\.css)(\")',r'\1\2\3',stdout2)
    with open(outrawname,'w') as fh:
        fh.write(stdout.decode())
    with open(outfname,'w') as fh:
        fh.write(stdout2)
    return ""

def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description='Conversion of sanitized LaTeX documents to XHTML')
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("xhtml_dir",help="Path to xhtml output directory")
    parser.add_argument("--timeout",help="Specify custom timeout")
    args = parser.parse_args()
    origdir = os.getcwd()
    global path
    global outpath
    global erroroutputpath
    global timeout
    path = args.directory
    outpath = args.xhtml_dir
    if not os.path.isdir(path):
        print("Error: {} is not a valid directory".format(path))
        sys.exit()
    if args.timeout:
        timeout = int(args.timeout)
        print("New timeout: {}s".format(timeout))
    outpath = os.path.join(os.path.abspath(outpath),'')
    validate_folder(outpath)
    os.chdir(outpath)
    erroroutputpath = os.path.join(os.path.split(os.path.normpath(outpath))[0],
    os.path.basename(os.path.normpath(path))+'_failed')
    validate_folder(erroroutputpath)
    print("Beginning processing of {}".format(path))
    print("Generating list of files with math...")
    filelist = getmathfiles(path)
    print("Generation complete.")
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Beginning processing...")
    outlist = pool.map(genxhtml,filelist)
    with open(outpath[:-1]+".log",'w') as fh:
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
