import os
import glob
import sys
import multiprocessing as mp
import re
from collections import Counter
import subprocess
from subprocess import PIPE
from core.funcs import *

def mse(filename):
    global outpath
    global path
    cleanname = os.path.splitext(os.path.basename(filename))[0]
    with open(filename, mode='r', encoding='latin-1') as fh:
        text = fh.read()
    text = re.sub(r'(?m)^%+.*$', '', text)
    text = re.sub(r"(?m)([^\\])\%+.*?$", r'\1', text)
    text = re.sub(r'\\begin\{comment\}.*?\\end\{comment\}','',text,re.DOTALL)
    packages = re.findall(r'\\usepackage(?:\[.*?\])?\{.*?\}',text)
    packages = '\n'.join(packages)
    stylefile = os.path.join(outpath,cleanname+'.sty')
    imgname = os.path.join(outpath,cleanname+'.png')
    with open(stylefile,'w') as fh:
        fh.write(packages)
    eqlabels = []
    occurrences = []
    equations = re.findall(r'(?s)\\begin\{equation\}.*?\\end\{equation\}|\\begin\{multline\}.*?\\end\{multline\}|\\begin\{gather\}.*?\\end\{gather\}|\\begin\{align\}.*?\\end\{align\}|\\begin\{flalign\*\}.*?\\end\{flalign\*\}|\\begin\{math\}.*?\\end\{math\}|[^\\]\\\[.*?\\\]|\$\$[^\^].*?\$\$',text)
    if len(equations)==0:
        return(-1)
    for equation in equations:
        x = re.match(r'\\label\{(.*?)\}',equation)
        if x:
            eqlabels.append(x.group(1).strip())
    labels = re.findall(r'\\eqref\{(.*?)\}',text) + re.findall(r'\\ref\{(.*?)\}',text)
    for label in labels:
        if label.strip() in eqlabels:
            occurrences.append(label.strip())
    count = Counter(occurrences).most_common(1)
    if count:
        if count[0][1]==1:
            rendereq = equations[0]
        else:
            rendereq = count[0][0]
    else:
        rendereq = equations[0]
    if len(rendereq)>1500:
        print("{}: MSE too long")
        return(-1)
    print("{}: Rendereq: {}".format(filename,rendereq))
    rendereq = rendereq.encode('utf-8')
    print("Outputting to: {}".format(imgname))
    preload = "--preload="+os.path.abspath(stylefile)
    mathimage = "--mathimage=" + os.path.abspath(imgname)
    print(preload)
    print(mathimage)
    try:
        proc = subprocess.Popen(["latexmlmath", preload,mathimage, "-"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        proc.communicate(rendereq)
    except:
        print("{}: Failed to generate image")
    return 0

def main():
    global outpath
    global path
    if len(sys.argv)>3:
        print("Error: require input/output directories", file=sys.stderr)
        sys.exit()
    path = os.path.join(sys.argv[1],'')
    outpath = os.path.join(sys.argv[2],'')
    if not os.path.isdir(path):
        print("Error: invalid input directory")
        sys.exit()
    if not os.path.isdir(outpath):
        os.makedirs(outpath)
    pool = mp.Pool(processes=mp.cpu_count())
    doclist = getmathfiles(path)
    doclist = map(os.path.abspath,doclist)
    list(map(mse,doclist))
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
