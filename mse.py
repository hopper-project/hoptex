import os
import glob
import sys
import multiprocessing as mp
import re
from collections import Counter
import subprocess
from core.funcs import *

def mse(filename):
    global outpath
    global path
    cleanname = os.path.splitext(os.path.basename(filename))[0]
    with open(filename, mode='r', encoding='latin-1') as fh:
        text = fh.read()
    text = remove_comments(text)
    packages = re.findall(r'\\usepackage(?:\[.*?\])?\{.*?\}',text)
    packages = '\n'.join(packages)
    stylefile = os.path.join(outpath,cleanname+'.sty')
    if(bibcodedict):
        try:
            bibcode = bibcodedict[cleanname]
        except:
            print("{}: No corresponding bibcode. Skipping...".format(filename))
            return("{}: No corresponding bibcode. Skipping...\n".format(filename))
        imgname = os.path.join(outpath,bibcode+'.png')
    else:
        imgname = os.path.join(outpath,cleanname+'.png')
    with open(stylefile,'w') as fh:
        fh.write(packages)
    eqlabels = []
    occurrences = []
    labeldict = {}
    isFirst = 0
    equations = grab_math(text)
    if len(equations)==0:
        return("{}: Something weird happened\n".format(filename))
    for equation in equations:
        x = re.findall(r'\\label\{(.*?)\}',equation)
        eqlabels = eqlabels + x
        for match in x:
            labeldict[match] = equation
    labels = re.findall(r'\\eqref\{(.*?)\}',text) + re.findall(r'\\ref\{(.*?)\}',text)
    for label in labels:
        if label.strip() in eqlabels:
            occurrences.append(labeldict[label.strip()])
    eqcount = Counter(occurrences).most_common()
    if eqcount:
        rendereq=eqcount[0][0]
        if len(eqcount)>1:
            firstcount = eqcount[0][1]
            pos = text.find(eqcount[0][0])
            for x in eqcount[1:]:
                if x[1]==firstcount:
                    xpos = text.find(x[0])
                    if xpos<pos:
                        pos=xpos
                        rendereq=x[0]
                else:
                    break
    else:
        rendereq = equations[0]
        isFirst = 1
    if len(rendereq)>1500:
        print("{}: MSE too long".format(filename))
        return("{}: MSE too long".format(filename))
    rendereq = rendereq.encode('utf-8')
    print("Outputting to: {}".format(imgname))
    preload = "--preload="+os.path.abspath(stylefile)
    mathimage = "--mathimage=" + os.path.abspath(imgname)
    try:
        proc = subprocess.Popen(["latexmlmath", preload,mathimage, "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate(rendereq, timeout=90)
    except:
        proc.kill()
        print("{}: Failed to generate image".format(filename))
        return("{}: Failed to generate image\n".format(filename))
    os.remove(stylefile)
    if isFirst:
        return("{}: first equation\n".format(filename))
    else:
        return("{}: {} occurrences\n".format(filename,eqcount[0][1]))

def rendereq(msetext,filename):
    global outpath
    global path
    if len(rendereq)>1500:
        print("{}: MSE too long".format(filename))
        return("{}: MSE too long".format(filename))
    rendereq = rendereq.encode('utf-8')
    print("Outputting to: {}".format(imgname))
    preload = "--preload="+os.path.abspath(stylefile)
    mathimage = "--mathimage=" + os.path.abspath(imgname)
    try:
        proc = subprocess.Popen(["latexmlmath", preload,mathimage, "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate(rendereq, timeout=90)
    except:
        proc.kill()
        print("{}: Failed to generate image".format(filename))
        return("{}: Failed to generate image\n".format(filename))
    os.remove(stylefile)
    if isFirst:
        return("{}: first equation\n".format(filename))
    else:
        return("{}: {} occurrences\n".format(filename,eqcount[0][1]))

def main():
    global outpath
    global path
    global bibcodedict
    bibcodedict = None
    if len(sys.argv)<3:
        print("Error: require input/output directories", file=sys.stderr)
        sys.exit()
    if len(sys.argv)==4:
        with open(sys.argv[3]) as metadata:
            mapping = metadata.readlines()
        bibcodedict = dict([x.strip().split(',') for x in mapping])
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
    tofile = pool.map(mse,doclist)
    log_file = outpath[:-1] + '.log'
    with open(log_file,'w') as fh:
        for x in tofile:
            fh.write(x+'\n')
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
