import os
import glob
import sys
import re
from collections import Counter
import subprocess
from core.funcs import *
import argparse
import tempfile

def cleantuple(tup):
    global outpath
    fname, text = tup
    output = os.path.join(outpath,fname+'.png')
    return(output,text)

def sqlgrab(filename):
    with open(filename,'r') as fh:
        text = fh.read()
    matches = re.findall(r'([\w]+)\s###([^#]+)###',text)
    return(matches)

def tsvgrab(filename):
    print("Loading TSV...")
    global outpath
    outlist = []
    with open(filename,'r') as fh:
        for line in fh:
            eqid, eqtext = line.split('\t')
            eqtext = eqtext.encode().decode('unicode_escape')
            outlist.append(cleantuple((eqid, eqtext)))
    return(outlist)

def render(tup):
    filepath, text = tup
    if os.path.isfile(filepath):
        return("")
    print("Processing {}".format(filepath))
    rendertext = text.encode('utf-8')
    try:
        with tempfile.TemporaryDirectory() as path:
            os.chdir(path)
            if(stylefile):
                proc = subprocess.Popen(["latexmlmath","--preload="+stylefile,"--mathimage="+filepath,"-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                proc = subprocess.Popen(["latexmlmath","--mathimage="+filepath,"-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(rendertext, timeout=90)
            stderr = stderr.decode()
            if len(stderr)>0:
                print("{}: {}".format(filepath,stderr))
                return("{}: {}\n".format(filepath,stderr))
    except:
        try:
            proc.kill()
        except:
            pass
        print("{}: Failed to generate image".format(filepath))
        return("{}: Failed to generate image\n".format(filepath))
    return("")

def main():
    global outpath
    global stylefile
    parser = argparse.ArgumentParser(description='Options for rendering LaTeX images of files')
    parser.add_argument('--sql',action='store_true', help="Use when passing in a sqlite.out file")
    parser.add_argument('--tsv', action='store_true', help="Use when passing in a tsv of the format EQID formula")
    parser.add_argument('--sty', help="Optional parameter for .sty file for use with latexmlmath")
    parser.add_argument("fname",help="Input file/folder")
    parser.add_argument("outdir",help="Path to output file/folder")
    args = parser.parse_args()
    fname = args.fname
    outpath = os.path.abspath(args.outdir)
    stylefile = args.sty
    pool = mp.Pool(processes=mp.cpu_count())
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    outpath = os.path.abspath(outpath)
    if(args.sql):
        matches = sqlgrab(args.fname)
        matches = list(map(cleantuple,matches))
        log = pool.map(render,matches)
    if(args.tsv):
        matches = tsvgrab(args.fname)
        log = pool.map(render,matches)
    else:
        print("Default functionality of script not yet implemented. ¯\_(ツ)_/¯")
    pool.close()
    pool.join()
    with open('templog.log','w') as fh:
        for x in log:
            if(x):
                fh.write(x)

if __name__ == '__main__':
    main()
