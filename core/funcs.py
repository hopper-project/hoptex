import glob
import os
import re
import multiprocessing as mp

def gettexfiles(path):
    absolute_path = os.path.abspath(path) + '/'
    file_list = glob.glob(os.path.join(absolute_path,'*.tex'))
    return file_list

def grabmath(text, split=0):
    delim = r'|'
    a = r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}'
    b = r'\\begin\{multline\*?\}.*?\\end\{multline\*?\}'
    c = r'\\begin\{gather\*?\}.*?\\end\{gather\*?\}'
    d = r'\\begin\{align\*?\}.*?\\end\{align\*?\}'
    e = r'\\begin\{flalign\*?\}.*?\\end\{flalign\*?\}'
    f = r'\\begin\{math\*?\}.*?\\end\{math\*?\}'
    g = r'[^\\]\\\[.*?\\\]'
    h = r'\$\$[^\^].*?\$\$'
    exprmatch = [a,b,c,d,e,f,g,h]
    if(split):
        tomatch = r'(?s)('+delim.join(exprmatch)+r')'
        matches = re.split(tomatch,text)
        return matches
    else:
        tomatch = r'(?s)' + delim.join(exprmatch)
        matches = re.findall(tomatch,text)
        return matches

def hasmath(filename):
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    finds = grabmath(text)
    return (filename, len(finds))

def getmathfiles(path):
    filelist = glob.glob(os.path.join(path,'*.tex'))
    outlist = []
    pool = mp.Pool(processes=mp.cpu_count())
    filelist = pool.map(hasmath,filelist)
    for texfile in filelist:
        if texfile[1]:
            outlist.append(os.path.abspath(texfile[0]))
    print("{} files with math".format(len(outlist)))
    pool.close()
    pool.join()
    return outlist
