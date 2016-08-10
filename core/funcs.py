import glob
import os
import re
import multiprocessing as mp

def gettexfiles(path):
    absolute_path = os.path.abspath(path) + '/'
    file_list = glob.glob(os.path.join(absolute_path,'*.tex'))
    return file_list

def hasmath(filename):
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    a = re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',text,re.DOTALL)
    b = re.findall(r'\\begin\{multline\}(.*?)\\end\{multline\}',text,re.DOTALL)
    c = re.findall(r'\\begin\{gather\}(.*?)\\end\{gather\}',text,re.DOTALL)
    d = re.findall(r'\\begin\{align\}(.*?)\\end\{align\}',text,re.DOTALL)
    e = re.findall(r'\\begin\{flalign\*\}(.*?)\\end\{flalign\*\}',text,re.DOTALL)
    f = re.findall(r'\\begin\{math\}(.*?)\\end\{math\}',text,re.DOTALL)
    g = re.findall(r'[^\\]\\\[(.*?)\\\]',text,re.DOTALL)
    h = re.findall(r'\$\$([^\^].*?)\$\$',text,re.DOTALL)
    l = re.findall(r'[^\\]\$(.*?)\$',text,re.DOTALL)
    m = re.findall(r'\\\((.*?)\\\)',text,re.DOTALL)
    finds = a + b + c + d + e + f + g + h
    return (filename, len(finds))

def getmathfiles(path):
    filelist = glob.glob(os.path.join(path,'*.tex'))
    outlist = []
    pool = mp.Pool(processes=mp.cpu_count())
    filelist = pool.map(hasmath,filelist)
    for texfile in filelist:
        if texfile[1]:
            outlist.append(os.path.abspath(texfile[0]))
    print(len(outlist))
    return outlist
    pool.close()
    pool.join()
