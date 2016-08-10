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
latexml = ''
latexmlpost = ''
def strip(param):
    return param.strip()

def genxhtml(filename):
    global latexml
    global latexmlpost
    print("{}: Start".format(filename))
    global outpath
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    #remove comments
    text = re.sub(r'(?m)^%+.*$','',text) #remove all comments at beginning of lines
    text = re.sub(r"(?m)([^\\])\%+.*?$",r'\1',text) #remove all remaining comments
    text = re.sub(r'\\begin\{comment\}.*?\\end\{comment\}','',text,re.DOTALL)
    #series of regex expressions
    body = re.findall(r'(?s)\\begin\{equation\}.*?\\end\{equation\}|\\begin\{multline\}.*?\\end\{multline\}|\\begin\{gather\}.*?\\end\{gather\}|\\begin\{align\}.*?\\end\{align\}|\\begin\{flalign\*\}.*?\\end\{flalign\*\}|\\begin\{math\}.*?\\end\{math\}|[^\\]\\\[.*?\\\]|\$\$[^\^].*?\$\$',text)
    for i, x in enumerate(body):
        if "\\[" in x:
            body[i] = re.sub(r'[^\\]\\\[',r'\[',x)
    #preamble = [re.match(r'(?s).*?\\begin{document}',text)]
    preamble = ['\\documentclass{article}\n','\\usepackage{amsmath}\n','\\usepackage{amsfonts}\n','\\usepackage{amssymb}\n','\\usepackage{bm}\n','\\begin{document}']
    #preamble = [text.split('\\begin{document}')[0] + "\n\\begin{document}"]
    postamble = ["\\end{document}"]
    output = '\n'.join(preamble+body+postamble)
    try:
        proc = subprocess.Popen(["latexml", "--quiet", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout, stderr = proc.communicate(output.encode(), timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML conversion failed - timeout".format(filename))
        return ""
    except:
        print("{}: Conversion failed".format(filename))
        return ""
    try:
        proc = subprocess.Popen(["latexmlpost", "--quiet", "--format=xhtml", "-"], stderr = PIPE, stdout = PIPE, stdin = PIPE)
        stdout2, stderr = proc.communicate(stdout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("{}: MathML postprocessing failed - timeout".format(filename))
        return ""
    fname = os.path.basename(filename)
    outfname = outpath + (os.path.splitext(fname)[0]+'.xhtml')
    with open(outfname,'w') as fh:
        fh.write(stdout2.decode())
    print("{}: Finish".format(filename))
    return stdout2

def main():
    origdir = os.getcwd()
    global path
    global outpath
    global latexml
    global latexmlpost
    path = '1506/'
    if(len(sys.argv)>1):
        path = os.path.join(str(sys.argv[1]),'')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a valid directory")
            sys.exit()
    path = os.path.abspath(path) + '/'
    print("Generating list of files with math...")
    latexml = 'LaTeXML/bin/latexml'
    latexmlpost = 'LaTeXML/bin/latexmlpost'
    if not (os.path.isfile(latexml) and os.path.isfile(latexmlpost)):
        print("Error: missing local copy of latexml. Exiting...",file=sys.stderr)
        sys.exit()
    latexml = os.path.abspath(latexml)
    latexmlpost = os.path.abspath(latexmlpost)
    filelist = getmathfiles(path)
    print("Generation complete.")
    outpath = path[:-1] + '_converted/'
    outpath = os.path.abspath(outpath) + '/'
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    os.chdir(outpath)
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    print("Beginning processing...")
    pool.map(genxhtml,filelist)
    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
