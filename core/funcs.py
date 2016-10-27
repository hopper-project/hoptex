import glob
import os
import re
import multiprocessing as mp

def gensanitized(text):
    text = removecomments(text)
    text = re.sub(r'(?s)([^\$])(\$[^\$]*?\$)(\$[^\$]*?\$)([^\$])',r"\1\2 \3\4",text,flags=re.DOTALL)
    docbody = re.findall(r'(?s)\\begin\{document\}.*?\\end\{document\}',text)
    if not docbody:
        return ""
    docbody = docbody[0]
    body = grabmath(docbody)
    packages = re.findall(r'(?s)\\usepackage(?:\[.*?\])?\{.*?\}',text)
    docclass = re.search(r'\\documentclass(?:\[.*?\])?\{.*?\}',text)
    if(docclass):
        docclass = docclass.group(0)+'\n'
        docclass = re.sub(r'\{.*?\}',"{article}",docclass)
    else:
        docclass = '\\documentclass{article}\n'
    preamble = [docclass] + packages + ['\\begin{document}\n']
    postamble = ["\\end{document}"]
    output = '\n'.join(preamble+body+postamble)
    return output


def gettexfiles(path):
    absolute_path = os.path.abspath(path) + '/'
    file_list = glob.glob(os.path.join(absolute_path,'*.tex'))
    return file_list

def removecomments(text):
    text = re.sub(r'(?m)^%+.*$','',text)
    text = re.sub(r"(?m)([^\\])\%+.*?$",r'\1',text)
    text = re.sub(r'(?s)\\begin\{comment\}.*?\\end\{comment\}','',text)
    return text

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
    text = removecomments(text)
    if(split):
        tomatch = r'(?s)('+delim.join(exprmatch)+r')'
        matches = re.split(tomatch,text)
        for i, x in enumerate(matches):
            matches[i] = re.sub(r'.\\\[',"\[",x) + '\n'
        matches.append("")
        return matches
    else:
        tomatch = r'(?s)' + delim.join(exprmatch)
        matches = re.findall(tomatch,text)
        for i, x in enumerate(matches):
            matches[i] = re.sub(r'.\\\[',"\[",x) + '\n'
        return matches

def hasmath(filename):
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    text = removecomments(text)
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

def getmathfromfilelist(files):
    pool = mp.Pool(processes=mp.cpu_count())
    filelist = pool.map(hasmath,files)
    for texfile in filelist:
        if texfile[1]:
            outlist.append(os.path.abspath(texfile[0]))
    print("{} files with math".format(len(outlist)))
    pool.close()
    pool.join()
    return outlist
