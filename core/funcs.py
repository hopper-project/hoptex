import glob
import os
import re
import multiprocessing as mp

def generate_sanitized_document(text):
    """Generates LaTeXML document containing only usepackage statements,
    begin & end document statements, and the extracted math.
    Returns string of the new text document
    """
    text = removecomments(text)
    text = re.sub(r'(?s)([^\$])(\$[^\$]*?\$)(\$[^\$]*?\$)([^\$])',r"\1\2 \3\4",text,flags=re.DOTALL)
    docbody = re.findall(r'(?s)\\begin\{document\}.*?\\end\{document\}',text)
    if not docbody:
        return ""
    docbody = docbody[0]
    body = grab_math(docbody)
    packages = re.findall(r'(?s)\\usepackage(?:\[.*?\])?\{.*?\}',text)
    docclass = re.search(r'\\documentclass(?:\[.*?\])?\{.*?\}',text)
    """Uses documentclass article if no custom document class is specified"""
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
    """Returns list of absolute paths to .tex files in a folder at path"""
    absolute_path = os.path.abspath(path)
    root, folders, files =  next(os.walk(absolute_path))
    for i, filename in enumerate(files):
        files[i] = os.path.join(root,filename)
    return files

def removecomments(text):
    """Takes LaTeX document text & returns document without any comments"""
    text = re.sub(r'(?m)^%+.*$','',text)
    text = re.sub(r"(?m)([^\\])\%+.*?$",r'\1',text)
    text = re.sub(r'(?s)\\begin\{comment\}.*?\\end\{comment\}','',text)
    return text


def grab_math(text, split=False):
    """Returns list of display math in the LaTeX document
    Enabling the split option returns the interspersed text, as separate
    entries in the list (e.g. text, eq, text, eq)"""
    delim = r'|'
    a = r'(?s)\\begin\{equation\*?\}.*?\\end\{equation\*?\}'
    b = r'(?s)\\begin\{multline\*?\}.*?\\end\{multline\*?\}'
    c = r'(?s)\\begin\{gather\*?\}.*?\\end\{gather\*?\}'
    d = r'(?s)\\begin\{align\*?\}.*?\\end\{align\*?\}'
    e = r'(?s)\\begin\{flalign\*?\}.*?\\end\{flalign\*?\}'
    f = r'(?s)\\begin\{math\*?\}.*?\\end\{math\*?\}'
    g = r'(?s)[^\\]\\\[.*?\\\]'
    h = r'(?s)\$\$[^\^].*?\$\$'
    exprmatch = [a,b,c,d,e,f,g,h]
    text = removecomments(text)
    if(split):
        tomatch = r'('+delim.join(exprmatch)+r')'
        matches = re.split(tomatch,text)
        for i, x in enumerate(matches):
            matches[i] = re.sub(r'.\\\[',"\[",x) + '\n'
        matches.append("")
        return matches
    else:
        tomatch =delim.join(exprmatch)
        matches = re.findall(tomatch,text)
        for i, x in enumerate(matches):
            matches[i] = re.sub(r'.\\\[',"\[",x) + '\n'
        return matches

def grab_inline_math(text, split=False):
    """Inline equivalent of grab_math"""
    text = removecomments(text)
    matchlist = []
    # matches = re.findall(r'(?<=[^\$])(\$[^\$]+?\$)(?=[^\$])|(?<=[^\$])(\$[^\$]+?\$)(\$[^\$]+?\$)(?=[^\$])',text)
    text = re.sub(r'\\\$','',text)
    matches = re.findall(r'(?<=[^\$])((?:\$[^\$]+?\$)+?)(?=[^\$])',text)
    if split:
        textlist = re.split(r'(?<=[^\$])((?:\$[^\$]+?\$)+?)(?=[^\$])',text)
        newtextlist = []
        matches = set(matches)
        for text in textlist:
            if text in matches:
                submatches = re.findall(r'\$.+?\$',text)
                for submatch in submatches:
                    newtextlist.append(submatch)
            else:
                newtextlist.append(text)
        return newtextlist
    else:
        for match in matches:
            submatches = re.findall(r'\$.+?\$',match)
            for submatch in submatches:
                matchlist.append(submatch)
            # if matches[0]:
            #     matchlist.append(match[0])
            # else:
            #     matchlist.append(match[1])
            #     matchlist.append(match[2])
        return matchlist

def grab_math_from_file(filename, split=False):
    """Combines grab_math and the prerequisite opening & reading in of .tex files"""
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return grab_math(text, split)

def grab_inline_math_from_file(filename):
    """Inline equivalent of grab_math_from_file"""
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return grab_inline_math(text)

def hasmath(filename):
    """Returns tuple of the filename and the number of display mode math
    equations in the text"""
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    text = removecomments(text)
    finds = grab_math(text)
    return (filename, len(finds))

def getmathfiles(path):
    """Returns a list of files that have math in them"""
    filelist = glob.glob(os.path.join(path,'*.tex'))
    outlist = []
    pool = mp.Pool(processes=mp.cpu_count())
    filelist = pool.map(hasmath,filelist)
    for texfile in filelist:
        if texfile[1]:
            outlist.append(os.path.abspath(texfile[0]))
    pool.close()
    pool.join()
    return outlist

def validate_folder(folder_path):
    """Checks that the given folder exists - if not, it creates the destination folder"""
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path)

def read_tsv(filename):
    """Returns a list of strings split on tabs from input file.
    The function yields one line at a time"""
    with open(filename,mode='r',encoding='latin-1') as fh:
        for line in fh:
            linesplit = line.rstrip('\n').split('\t')
            yield linesplit

def mask(text):
    """Converts the equation into a tsv-friendly format"""
    return repr(text)[1:-1]

def unmask(text):
    """Converts the 'masked' equation back to its original form"""
    return text.encode().decode('unicode-escape')
