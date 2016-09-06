import sys #handling arguments passed to function
import glob #file path handling
import os #checking files and writing to/from files
import re #regex matching
import multiprocessing as mp #drastic speedups when implemented on an i7-4710HQ
import subprocess
from subprocess import PIPE
from core.funcs import *

path = ''
outpath = ''

def writesanitized(sanitized,cleanname):
    global erroroutputpath
    outfile = os.path.join(erroroutputpath,cleanname+'.tex')
    with open(outfile,'w') as fh:
        fh.write(sanitized)

def genxhtml(filename):
    global outpath
    cleanname = os.path.splitext(os.path.basename(filename))[0]
    outfname = outpath + cleanname+'.xhtml'
    if os.path.isfile(outfname):
        # print("{}: Already generated".format(filename))
        return ""
    # print("{}: Start".format(filename))
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    output = gensanitized(text)
    if len(output)==0:
        print("{}: Error - no body found".format(filename))
        return("{}: Error - no body found".format(filename))
    try:
        proc = subprocess.Popen(["latexml", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout, stderr = proc.communicate(output.encode(), timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML conversion failed - timeout".format(filename))
        writesanitized(output,cleanname)
        return "{}: MathML conversion failed - timeout".format(filename)
    except:
        print("{}: Conversion failed".format(filename))
        writesanitized(output,cleanname)
        return "{}: Conversion failed".format(filename)
    try:
        proc = subprocess.Popen(["latexmlpost", "--format=xhtml", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout2, stderr = proc.communicate(stdout, timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML postprocessing failed - timeout".format(filename))
        writesanitized(output,cleanname)
        return "{}: MathML postprocessing failed - timeout".format(filename)
    if len(stdout2.strip())==0:
        print("{}: Conversion failed".format(filename))
        writesanitized(output,cleanname)
        return("{}: Conversion failed".format(filename))
    stdout2 = stdout2.decode()
    stdout2 = re.sub(r'(href\=\").*?(LaTeXML\.css)(\")',r'\1\2\3',stdout2)
    stdout2 = re.sub(r'(href=\").*?(ltx-article\.css)(\")',r'\1\2\3',stdout2)
    with open(outfname,'w') as fh:
        fh.write(stdout2)
    # print("{}: Finish".format(filename))
    return ""

def main():
    origdir = os.getcwd()
    global path
    global outpath
    global erroroutputpath
    if len(sys.argv)==1:
        print("Error: must pass in one or more valid directories")
    path = os.path.join(str(sys.argv[1]),'')
    if not os.path.isdir(path):
        print("Error: {} is not a valid directory".format(x))
        sys.exit()
    erroroutputpath = os.path.join(os.path.join(outpath,os.pardir)[:-1],os.path.abspath(path[:-1]))+'_failed/'
    print("Beginning processing of {}".format(path))
    path = os.path.abspath(path) + '/'
    print("Generating list of files with math...")
    filelist = getmathfiles(path)
    print("Generation complete.")
    if len(sys.argv)==3:
        outpath = os.path.join(sys.argv[2],'')
    else:
        outpath = path[:-1] + '_converted/'
    outpath = os.path.abspath(outpath) + '/'
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    os.chdir(outpath)
    if not os.path.isdir(erroroutputpath):
        os.makedirs(erroroutputpath)
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Beginning processing...")
    outlist = pool.map(genxhtml,filelist)
    with open(outpath[:-1]+".log",'w') as fh:
        for message in outlist:
            if len(message)>0:
                fh.write(message+'\n')
    pool.close()
    pool.join()
    os.chdir(origdir)


if __name__ == '__main__':
    main()
