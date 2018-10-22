import glob
import os
import re
import multiprocessing as mp
import gc

global a
global b
global c
global d
global e
global f
global g
global i
global j

#regex patterns

a = r'(?s)\\begin\{equation\*?\}.*?\\end\{equation\*?\}'
b = r'(?s)\\begin\{multline\*?\}.*?\\end\{multline\*?\}'
c = r'(?s)\\begin\{gather\*?\}.*?\\end\{gather\*?\}'
d = r'(?s)\\begin\{align\*?\}.*?\\end\{align\*?\}'
e = r'(?s)\\begin\{flalign\*?\}.*?\\end\{flalign\*?\}'
f = r'(?s)\\begin\{math\*?\}.*?\\end\{math\*?\}'
g = r'(?s)(?<!\\)\\\[.*?\\\]'
h = r'(?s)\$\$[^\^].*?\$\$'
i = r'(?s)\\begin\{eqnarray\*?\}.*?\\end\{eqnarray\*?\}'
j = r'(?s)\\\[.*?\\\]'

# named capturing versions of the respective equations above
ca = r'(?s)(?P<equation>\\begin\{equation\*?\}(?P<math>.*?)\\end\{equation\*?\})'
cb = r'(?s)(?P<multline>\\begin\{multline\*?\}(?P<math>.*?)\\end\{multline\*?\})'
cc = r'(?s)(?P<gather>\\begin\{gather\*?\}(?P<math>.*?)\\end\{gather\*?\})'
cd = r'(?s)(?P<align>\\begin\{align\*?\}(?P<math>.*?)\\end\{align\*?\})'
ce = r'(?s)(?P<flalign>\\begin\{flalign\*?\}(?P<math>.*?)\\end\{flalign\*?\})'
cf = r'(?s)(?P<dmath>\\begin\{math\*?\}(?P<math>.*?)\\end\{math\*?\})'
cg = r'(?s)(?P<bracket>(?<!\\)\\\[(?P<math>.*?)\\\])'
ch = r'(?s)(?P<dollarsign>\$\$(?P<math>[^\^].*?)\$\$)'
ci = r'(?s)(?P<eqnarray>\\begin\{eqnarray\*?\}(?P<math>.*?)\\end\{eqnarray\*?\})'

r1 = r'\\nonumber(?![A-Za-z\@\*])'
r2 = r'\\tag(?![A-Za-z\@\*])'
r3 = r'(?<!\\)&'
r4 = r'\\hspace\{.+?\}'
r5 = r'\\times(?![A-Za-z\@\*])'
r6 = r'\\lefteqn(?![A-Za-z\@\*])'
r7 = r'\\righteqn(?![A-Za-z\@\*])'
r8 = r'\\qedhere(?![A-Za-z\@\*])'
r9 = r'\\label\{.+?\}'
r10 = r'\\q{0,1}quad'

to_remove = [r1,r2,r3,r4,r5,r6,r7,r8,r9,r10]

multiline_list = [cb,cc,cd,ce,ci]

expr_list = [a,b,c,d,e,f,g,h,i,j]

cap_expr_list = [ca,cb,cc,cd,ce,cf,cg,ch,ci]

non_capture_math = r'('+'|'.join(expr_list)+r')'

inline_pattern =r'(?<=[^\$])((?:\$[^\$]+?\$)+?)(?=[^\$])'


# REGEX FOR SEARCHING
bdoc = r"\\begin{document}"
edoc = r"\\end{document}"

body_pattern = r'(?s)\\begin{document}.*?\\end{document}'

# Functions used throughout the hoptex library go here

def grab_body(text):
    text = remove_comments(text)
    match = re.search(body_pattern,text)
    if match:
        return match.group(0)
    else:
        return ''

def remove_inline_math(text):
    text = re.sub(inline_pattern,'',text)
    return text

def is_math(text):
    if re.match(non_capture_math,text):
        return True
    return False

def is_multiline(text):
    """Returns True if expression is align,flalign,eqnarray,gather, or multline"""
    for expr in multiline_list:
        if re.match(expr,text):
            return True
    return False

def remove_whitespace(text):
    """Believe it or not, this function removes whitespace from text"""
    text = re.sub(r'\s','',text)
    return text

def split_multiline(text):
    """Splits an equation environment on the LaTeX newline ('\\\\') character"""
    textlist = re.split(r'\\\\',text)
    for i, x in enumerate(textlist):
        textlist[i] = remove_whitespace(x)
    return textlist

def enforce_newlines(text):
    """Ensures a newline character after LaTeX newline"""
    text = re.sub(r'\\\\(?!\n)',r'\\\\\n',text)
    return text

def sanitize_equation(text, complete=False):
    for expr in to_remove:
        text = re.sub(expr,'',text)
    if complete:
        text = re.sub(r'(?:\\\\)+','',text)
    return text

def standardize_equation(text):
    for expr in cap_expr_list:
        match = re.match(expr,text)
        if match:
            new_eq = sanitize_equation(match.group('math'))
            return new_eq

def flatten_equation(text):
    text = remove_whitespace(standardize_equation(text))
    return text

def split_multiline(text):
    text = flatten_equation(text)
    newtextlist = re.split(r'(?:\\\\)+',text)
    return newtextlist


def load_document(filename):
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return text

def generate_sanitized_document(text):
    """Generates LaTeXML document containing only usepackage statements,
    begin & end document statements, and math found between the begin and end
    document statements.
    Returns string of the new text document
    """
    text = remove_comments(text)
    text = remove_inline_math(text)
    if not (re.search(bdoc,text) and re.search(edoc,text)):
        return ""
    body = grab_math(text)
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
    output = '\n\n'.join(preamble+body+postamble)
    return output

def sanitized_doc_from_file(filename):
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return generate_sanitized_document(text)

def gettexfiles(path):
    """Returns list of absolute paths to .tex files in a folder at path"""
    absolute_path = os.path.abspath(path)
    root, folders, files =  next(os.walk(absolute_path))
    for i, filename in enumerate(files):
        files[i] = os.path.join(root,filename)
    return files

def remove_comments(text):
    """Takes LaTeX document text & returns document without any comments"""
    text = re.sub(r'(?<=\n)%.+?\n','',text)
    text = re.sub(r'(?<!\\)%\n','',text)
    text = re.sub(r'(?<!\\)%.*?\n','\n',text)
    text = re.sub(r'(?s)\\begin\{comment\}.*?\\end\{comment\}','',text)
    return text

def remove_comment_newlines(text):
    """Removes percentages immediately followed by newlines"""
    text = re.sub(r'%\n','',text)
    return text

def clean_inline_math(text):
    text = remove_comments(text)
    text = re.sub(r'(?<!\\)((?:\\\\)*)(\\\$)','\1escapeddollarsign',text)
    matches = re.findall(inline_pattern,text)
    for match in matches:
        sub_eqs = re.findall(r'(?s)\$.+?\$',match)
        if len(sub_eqs)>0:
            new_inline_text = ' '.join(sub_eqs)
            text  = text.replace(match,new_inline_text)
    text = re.sub(ch,r' \1 ',text)
    text = re.sub('escapeddollarsign',r'\\\$',text)
    return text

def grab_math(text, split=False):
    """Returns list of display math in the LaTeX document
    Enabling the split option returns the interspersed text, as separate
    entries in the list (e.g. text, eq, text, eq)"""
    text = grab_body(text)
    text = clean_inline_math(text)
    if(split):
        matches = re.split(non_capture_math,text)
        return matches
    else:
        matches = re.findall(non_capture_math,text,re.MULTILINE)
        return matches

def grab_inline_math(text, split=False):
    """Inline equivalent of grab_math"""
    text = grab_body(text)
    text = clean_inline_math(text)
    matchlist = []
    matches = re.findall(inline_pattern,text)
    if split:
        textlist = re.split(inline_pattern,text)
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
        return matchlist

def grab_math_from_file(filename, split=False):
    """Combines grab_math and the prerequisite opening & reading in of .tex files"""
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    grabbed_math = grab_math(text, split)
    return (filename.split('/')[-1],grabbed_math)

def grab_inline_math_from_file(filename):
    """Inline equivalent of grab_math_from_file"""
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    return (filename.split('/')[-1],grab_inline_math(text))

def hasmath(filename):
    """Returns tuple of the filename and the number of display mode math
    equations in the text"""
    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    text = remove_comments(text)
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
