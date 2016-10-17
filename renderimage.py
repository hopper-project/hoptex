import os
import glob
import sys
import re
from collections import Counter
import subprocess
from core.funcs import *
import argparse

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

def render(tup):
    outpath, text = tup
    rendertext = text.encode('utf-8')
    try:
        proc = subprocess.Popen(["latexmlmath","--mathimage="+os.path.abspath(outpath),"-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(rendertext, timeout=90)
        stderr = stderr.decode()
        if len(stderr)>0:
            print("{}: {}".format(outpath,stderr))
            return("{}: {}\n".format(outpath,stderr))
    except:
        try:
            proc.kill()
        except:
            pass
        print("{}: Failed to generate image".format(outpath))
        return("{}: Failed to generate image\n".format(outpath))
    return("")

def main():
    global outpath
    parser = argparse.ArgumentParser(description='Options for rendering LaTeX images of files')
    parser.add_argument('--sql',action='store_true', help="Use when passing in a sqlite.out file")
    parser.add_argument("fname",help="Path to sql file (requires --sql flag), or folder of .tex files.")
    parser.add_argument("outdir",help="Path to output file")
    args = parser.parse_args()
    fname = args.fname
    outpath = args.outdir
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    if(args.sql):
        matches = sqlgrab(args.fname)
        matches = list(map(cleantuple,matches))
        log = list(map(render,matches))
        with open('templog.log','w') as fh:
            for x in log:
                if(x):
                    fh.write(x)
    else:
        print("Default functionality of script not yet implemented. ¯\_(ツ)_/¯")

if __name__ == '__main__':
    main()
