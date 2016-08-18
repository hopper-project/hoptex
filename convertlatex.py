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
def strip(param):
    return param.strip()

def genxhtml(filename):
    global outpath
    fname = os.path.basename(filename)
    outfname = outpath + (os.path.splitext(fname)[0]+'.xhtml')
    if os.path.isfile(outfname):
        print("{}: Already generated".format(filename))
        return ""
    # print("{}: Start".format(filename))
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    #remove comments
    text = re.sub(r'(?m)^%+.*$','',text) #remove all comments at beginning of lines
    text = re.sub(r"(?m)([^\\])\%+.*?$",r'\1',text) #remove all remaining comments
    text = re.sub(r'\\begin\{comment\}.*?\\end\{comment\}','',text,re.DOTALL)
    #series of regex expressions
    body = re.findall(r'(?s)\\begin\{equation\}.*?\\end\{equation\}|\\begin\{multline\}.*?\\end\{multline\}|\\begin\{gather\}.*?\\end\{gather\}|\\begin\{align\}.*?\\end\{align\}|\\begin\{flalign\*\}.*?\\end\{flalign\*\}|\\begin\{math\}.*?\\end\{math\}|[^\\]\\\[.*?\\\]|\$\$[^\^].*?\$\$',text)
    for i, x in enumerate(body):
        body[i] = re.sub(r'.\\\[',"\[",x) + '\n'
    packages = re.findall(r'\\usepackage(?:\[.*?\])?\{.*?\}',text)
    for i, x in enumerate(packages):
        packages[i] = x + '\n'
    preamble = ['\\documentclass{article}\n'] + packages + ['\\begin{document}\n']
    postamble = ["\\end{document}"]
    output = '\n'.join(preamble+body+postamble)
    try:
        proc = subprocess.Popen(["latexml", "--quiet", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout, stderr = proc.communicate(output.encode(), timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML conversion failed - timeout".format(filename))
        return "{}: MathML conversion failed - timeout".format(filename)
    except:
        print("{}: Conversion failed".format(filename))
        return "{}: Conversion failed".format(filename)
    try:
        proc = subprocess.Popen(["latexmlpost", "--quiet", "--format=xhtml", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout2, stderr = proc.communicate(stdout, timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML postprocessing failed - timeout".format(filename))
        return "{}: MathML postprocessing failed - timeout".format(filename)
    with open(outfname,'w') as fh:
        fh.write(stdout2.decode())
    # print("{}: Finish".format(filename))
    return ""

def main():
    origdir = os.getcwd()
    global path
    global outpath
    if len(sys.argv)==1:
        print("Error: must pass in one or more valid directories")
    path = os.path.join(str(sys.argv[1]),'')
    if not os.path.isdir(path):
        print("Error: {} is not a valid directory".format(x))
        sys.exit()
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
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Beginning processing...")
    outlist = pool.map(genxhtml,filelist)
    with open(outpath[:-1]+".log",'w') as fh:
        for message in outlist:
            if len(message)>0:
                fh.write(message)
        pool.close()
        pool.join()
        os.chdir(origdir)


if __name__ == '__main__':
    main()
