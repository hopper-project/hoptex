"""
Parse macros in LaTeX source code. Supported macros include:
    - newcommand/renewcommand(*)
    - DeclareMathOperator
    - def
    - input
"""

import sys
import re
import os
import multiprocessing as mp
import time #probably not needed
import argparse
import tarfile
import time



from core.funcs import *

global diag_message
global timeout
global rcp
global outdirectory

diag_message = False
timeout = 10
rcp = ['\\def','\\newcommand','\\renewcommand','\\DeclareMathOperator']

r0 = r'(?s)\\def\s*(?P<name>\\[\w@]+|\\.)\s*'
r1 = r'(?P<sep1>[^#\{]+)?(?P<arg1>#1)?(?P<sep2>[^#\{]+)?'
r2 = r'(?P<arg2>#2)?(?P<sep3>[^#\{]+)?'
r3 = r'(?P<arg3>#3)?(?P<sep4>[^#\{]+)?'
r4 = r'(?P<arg4>#4)?(?P<sep5>[^#\{]+)?'
r5 = r'(?P<arg5>#5)?(?P<sep6>[^#\{]+)?'
r6 = r'(?P<arg6>#6)?(?P<sep7>[^#\{]+)?'
r7 = r'(?P<arg7>#7)?(?P<sep8>[^#\{]+)?'
r8 = r'(?P<arg8>#8)?(?P<sep9>[^#\{]+)?'
r9 = r'(?P<arg9>#9)?(?P<sep10>[^#\{]+)?(?=\{)'

#Regex pattern for seeking & retrieving args & separators for def
def_pattern = r0+r1+r2+r3+r4+r5+r6+r7+r8+r9

math_pattern = r"\\DeclareMathOperator(\*)?"

def_token = r'\\def(?![A-z])'

input_pattern = r'\\input\s*\{\s*([^\s\\]+)\}|\\input(?![A-za-z@])\s*([^\s\\]+)'

newcommand_pattern = r'\\newcommand\*?'

renewcomand_pattern = r'\\renewcommand\*?'

begin_document = r'\\begin\{document\}'
"""
A lot of the code below is necessary because Python has been taking 5 years and counting
to put the vastly superior 'regex' module from PyPI into stdlib
"""

def verbose(*args):
    global diag_message
    if diag_message:
        for text in args:
            print(text)

def balanced_delim_checker(text,delim):
    opening = [delim[0]]
    closing = [delim[1]]
    stack = []
    for char in text:
        if char in opening:
            stack.append(char)
        elif char in closing:
            if stack:
                if opening.index(stack[-1])==closing.index(char):
                    stack.pop()
                    continue
                return False
    return True

def balanced_brackets(text):
    return balanced_delim_checker(text,"[]")

def balanced_braces(text):
    return balanced_delim_checker(text,"{}")

def take_while(text_evaluator, text):
    out = []
    for i, character in enumerate(text):
        if text_evaluator(character):
            out.append(character)
        else:
            return (''.join(out),text[i:])

def take_group(text):
    group = []
    if text[0]=='{':
        stack = []
        for i,character in enumerate(text):
            group.append(character)
            if character=='{':
                stack.append(character)
            elif character=='}':
                stack.pop()
                if len(stack)==0:
                    break
        return (''.join(group),text[i+1:])
    else:
        return('',text)

def take_whitespace(text):
    spaces = []
    for character in text:
        if character in "\t\n %":
            spaces.append(character)
        else:
            break
    return (''.join(spaces), text[len(spaces):])

def take_token(text):
    token = []
    if text[0]=='\\':
        token.append('\\')
        if not re.match(r'[\w@\*]',text[1]):
            if text[1]=='\\':
                return('',text)
            token.append(text[1])
            return (''.join(token),text[2:])
        for i, character in enumerate(text[1:]):
            if re.match(r'[\w@\*]',character):
                token.append(character)
            else:
                break
        return(''.join(token),text[len(token):])
    else:
        return('',text)

def take_argument(text):
    if re.match(r'#[1-9]',text):
        return(text[:2],text[2:])
    else:
        return('',text)

def take_match(text,match_text):
    match = []
    for i, character in enumerate(match_text):
        if character==text[i]:
            match.append(character)
        else:
            print("Matching failed:")
            print(match_text)
            raise ValueError('Match not found')
    return (''.join(match),text[len(match):])

def take_param(text):
    param = []
    if text[0]=='[':
        stack = []
        for i, character in enumerate(text):
            param.append(character)
            if character=='[':
                stack.append(character)
            if character==']':
                stack.pop()
                if len(stack)==0:
                    break
        return (''.join(param),text[len(param):])
    else:
        return('',text)

def take_word(text):
    word = []
    for character in text:
        if character in ' \t\n\\':
            break
        else:
            word.append(character)
    return(''.join(word),text[len(word):])

def take_general(text):
    if text[0]=="{":
        return take_group(text)
    elif text[0]=="\\":
        return take_token(text)
    else:
        return(text[0],text[1:])

def take_general_alt(text):
    if text[0]=="{":
        return take_group(text)
    else:
        return take_word(text)

def take_length(text,length):
    return (text[0:length],text[length:])

def parse(text,sequence):
    output = []
    a, b = None, text
    for operation in sequence:
        a, b = operation(b)
        output.append(a)
    return (output,b)

def extract_group(text):
    if balanced_braces(text) and text[0]=='{':
        return text[1:-1]
    else:
        return text

def extract_group_total(text):
    while balanced_braces(text) and text[0]=='{':
        text = text[1:-1]
    return text

def enclose_in_group(text):
    if balanced_braces(text) and text[0]=='{':
        return text
    else:
        return '{' + text + '}'


def num_valid(items):
    val = 0
    for item in items:
        if item:
            val += 1
    return val

#Parsing sequences
newcommand_sequence = [take_token, take_whitespace, take_general,
                        take_whitespace, take_param, take_whitespace,
                        take_param, take_whitespace, take_general]

math_operator_sequence = [take_whitespace,take_general,
                            take_whitespace,take_general]


def_input_sequence = [take_token,take_whitespace]

renewcommand_sequence = newcommand_sequence

sbalsup = r"""\newcommand\wbalsup [1]{  This is the Wikibook about LaTeX supported by #1}"""

class macro:
    """Template for the macro class - stores def, newcommand, renewcommand,
    and DeclareMathOperator.
    """
    def __init__(self):
        # Initialize all variables to empty
        self.arg1 = self.arg2 = self.arg3 = self.arg4 = self.arg5 = ''
        self.arg6 = self.arg7 = self.arg8 = self.arg9 = self.sep1 = ''
        self.sep2 = self.sep3 = self.sep4 = self.sep5 = self.sep6 = ''
        self.sep7 = self.sep8 = self.sep9 = self.sep10 = self.name = ''
        self.type = self.default = self.definition = self.text = ''
        self.asterisk = ''
        self.arg_count = 0

    def macro_text(self):
        global verbose
        verbose("Replace: {}".format(self.text))
        return self.text

    def load_def(self, match_obj,text):
        #copies over to avoid mutating the original def list
        global verbose
        global rcp
        dictionary = match_obj.groupdict()
        self.parameter_text = match_obj.group(0)
        self.sep1 = dictionary['sep1']
        self.sep2 = dictionary['sep2']
        self.sep3 = dictionary['sep3']
        self.sep4 = dictionary['sep4']
        self.sep5 = dictionary['sep5']
        self.sep6 = dictionary['sep6']
        self.sep7 = dictionary['sep7']
        self.sep8 = dictionary['sep8']
        self.sep9 = dictionary['sep9']
        self.arg1 = dictionary['arg1']
        self.arg2 = dictionary['arg2']
        self.arg3 = dictionary['arg3']
        self.arg4 = dictionary['arg4']
        self.arg5 = dictionary['arg5']
        self.arg6 = dictionary['arg6']
        self.arg7 = dictionary['arg7']
        self.arg8 = dictionary['arg8']
        self.arg9 = dictionary['arg9']
        self.name = dictionary['name']
        self.arg_count = num_valid([self.arg1,self.arg2,self.arg3,
        self.arg4,self.arg5,self.arg6,self.arg7,self.arg8,self.arg9])
        self.definition = take_group(text)[0]
        self.type = "\\def"
        self.text = self.parameter_text + self.definition
        for name in rcp:
            match_pattern = re.escape(name)
            if re.search(match_pattern+r'(?![\w\@])',self.definition):
                self.text = ''
                self.definition = ''
                verbose("Encountered nested definition - erasing")
        if re.search(r'(?<!\\)#{2,}[0-9]',self.definition):
            print("Nested macros detected erasing")
            self.definition = ''
        self.definition = re.sub(re.escape(self.name),'',self.definition)
        verbose("def")
        verbose("{} arguments".format(self.arg_count))
        verbose(self.name)
        verbose(self.definition)
        verbose("end def")


    def load_mathoperator(self,text, starting):
        results = parse(text,math_operator_sequence)[0]
        self.text = starting + ''.join(results)
        if starting[-1]=='*':
            self.asterisk = '*'
        self.type = '\\DeclareMathOperator'
        self.arg1 = enclose_in_group(results[1])
        self.arg2 = enclose_in_group(results[3])
        self.name = extract_group(self.arg1)
        verbose("Mathoperator")
        verbose(self.arg1)
        verbose(self.arg2)
        verbose("End mathoperator")

    def load_newcommand(self,text):
        global rcp
        results = parse(text,newcommand_sequence)[0]
        self.text = ''.join(results)
        self.type = results[0]
        self.name = extract_group_total(results[2]).strip()
        self.arg_count = results[4]
        self.default = results[6]
        self.definition = results[8]
        if self.arg_count:
            try:
                self.arg_count = int(self.arg_count[1:-1])
            except:
                print(self.arg_count)
                ValueError("Error parsing argcount: {}".format(self.arg_count))
        else:
            self.arg_count = 0
        for name in rcp:
            match_pattern = re.escape(name)
            if re.search(match_pattern+r'(?![\w\@])',self.definition):
                self.text = ''
                self.definition = ''
                verbose("Encountered nested definition - erasing")
        self.definition = re.sub(re.escape(self.name),'',self.definition)
        verbose("newcommand: {}".format(self.name))
        verbose("Default parameter: {}".format(self.default))
        verbose("{} args".format(self.arg_count))
        verbose(self.definition)
        verbose("End newcommand")

    def load_renewcommand(self,text):
        results = parse(text,newcommand_sequence)[0]
        self.text = ''.join(results)
        self.type = results[0]
        if self.type[-1]=='*':
            self.asterisk = '*'
            self.type = self.type[:-1]
        self.name = extract_group_total(results[2]).strip()
        self.arg_count = results[4]
        self.default = results[6]
        self.definition = results[8]
        if self.arg_count:
            self.arg_count = int(self.arg_count[1:-1])
        else:
            self.arg_count = 0
        for name in rcp:
            match_pattern = re.escape(name)
            if re.search(match_pattern+r'(?![\w\@])',self.definition):
                self.text = ''
                self.definition = ''
                verbose("Encountered nested definition - erasing")


    def substitute_arguments(self, arglist, default_arg=''):
        """Accepts a list of the values of args, returns definition with args"""
        text = self.definition
        if self.type=='\\def':
            for i, arg in enumerate(arglist):
                text = text.replace('#'+str(i+1),arg)
            return(text)
        elif self.type=='\\newcommand':
            verbose("Newcommand arglist: {}".format(arglist))
            if self.default:
                if default_arg:
                    verbose("Replacing with new default")
                    text = text.replace('#1',default_arg[1:-1])
                else:
                    verbose("Replacing with original default")
                    text = text.replace('#1',self.default[1:-1])
                #check for whether or not a new default exists
                for i, arg in enumerate(arglist):
                    text = text.replace('#'+str(i+2),arg)
                return text
            else:
                for i, arg in enumerate(arglist):
                    text = text.replace('#'+str(i+1),arg)
                return text
        elif self.type=='\\renewcommand':
            if self.default:
                if default_arg:
                    text = text.replace('#1',default_arg[1:-1])
                else:
                    text = text.replace('#1',self.default[1:-1])
                    for i, arg in enumerate(arglist):
                        text = text.replace('#'+str(i+2),arg)
                    return text
            else:
                for i, arg in enumerate(arglist):
                    text = text.replace('#'+str(i+1),arg)
                return text
        else:
            pass

    def parse_expression(self,text):
        parsed = []
        verbose(self.type)
        verbose(self.name)
        if self.type=='\\def':
            a, b = parse(text,def_input_sequence)
            if a[0]!=self.name:
                verbose("CRITICAL ERROR: MISMATCHED TOKEN")
                verbose("EXPECTED: {}, MATCHED: {}DELIM".format(self.name,a[0]))
            if self.arg_count==0:
                return (self.definition, b)
            else:
                if self.sep1:
                    a, b = take_match(b, self.sep1)
                arglist = [self.arg1,self.arg2,self.arg3,self.arg4,
                self.arg5,self.arg6,self.arg7,self.arg8,self.arg9]
                seplist = [self.sep2,self.sep3,self.sep4,
                self.sep5,self.sep6,self.sep7,self.sep8,self.sep9,self.sep10]
                for i, argument in enumerate(arglist):
                    if argument:
                        if seplist[i]:
                            match_index = b.index(seplist[i])
                            # match_index now contains the index of the separator
                            a, b = take_length(b, match_index)
                            parsed.append(a)
                            a, b = take_match(b,seplist[i])
                        else:
                            a,b = take_general(b)
                            parsed.append(a)
                    else:
                        break
                verbose("PARSED: {}".format(parsed))
            return(self.substitute_arguments(parsed),b)
        elif self.type == '\\renewcommand':
            verbose("Returning renewcommand")
            a, b = take_token(text)
            if self.arg_count == 0:
                return(self.definition,b)
            a, b = take_whitespace(b)
            default, b = take_param(b)
            a, b = take_whitespace(b)
            num_args = self.arg_count
            if default:
                num_args -= 1
            parsing = [take_general, take_whitespace] * (num_args-1)
            parsing.append(take_general)
            results, b = parse(b,parsing)
            results = [results[x] for x in range(0,len(results)+1,2)]
            return (self.substitute_arguments(results,default),b)
        elif self.type == "\\newcommand":
            verbose("Returning newcommand")
            verbose(self.name)
            a, b = take_token(text)
            verbose(a)
            if self.arg_count == 0:
                return(self.definition,b)
            a, b = take_whitespace(b)
            default, b = take_param(b)
            if(default):
                verbose("NEW DEFAULT: {}".format(default))
            a, b = take_whitespace(b)
            num_args = self.arg_count
            if default:
                num_args -= 1
            verbose("argument count: {}".format(self.arg_count))
            parsing = [take_general,take_whitespace]*(num_args-1)
            parsing.append(take_general)
            results, b = parse(b,parsing)
            results = [results[x] for x in range(0,len(results)+1,2)]
            verbose("results: {}".format(results))
            verbose("Substituted",self.substitute_arguments(results,default))
            return(self.substitute_arguments(results,default),b)
        elif self.type == "\\DeclareMathOperator":
            a, b = take_token(text)
            return("\\operatorname"+self.asterisk+self.arg2,b)
        else:
            a, b = take_general(text)
            return("",b)


examplestr = r"""\def\graph#1#2#3{
\begin{figure}[htb]
\centering
\includegraphics[width=3.5 in]{#1}
%\centerline{\epsfxsize = 4 in \epsffile{#1}} \caption{#2}
\label{#3}
\end{figure}
}"""

tokentest = r'\token is here'

simpletest = r'\def \lf {\left}'

multiline = r'\def\va{{\bf a}} \def\vb{{\bf b}} \def\vc{{\bf c}} \def\vd{{\bf d}}'

def find_main_file(folder):
    """Iterates over every document in the folder, and returns the path to the
    file with begin/end document statements
    """
    folder = os.path.abspath(folder)
    files = next(os.walk(folder))[2]
    for filename in files:
        if os.path.splitext(filename)[1].lower()!='.tex':
            continue
        with open(os.path.join(folder,filename),mode='r',encoding='latin-1') as fh:
            text = fh.read()
        if re.search(r'(?s)\\begin\{document\}.*?\\end\{document\}',text):
            return os.path.join(folder,filename)
    return ""


doctext = load_document('macroexamples.tex')

def load_inputs(path):
    with open(path,mode='r',encoding='latin-1') as fh:
        text = fh.read()+'\n'
    folder = os.path.split(path)[0]
    text = remove_comments(text)
    for match in re.finditer(input_pattern,text):
        if match.group(1):
            external = match.group(1)
        else:
            external= match.group(2)
        suffix = os.path.splitext(external)[1]
        external = os.path.splitext(external)[0]+'.tex'
        external = os.path.join(folder,external)
        external_document = ""
        if os.path.isfile(external):
            with open(external,mode='r',encoding='latin-1') as fh:
                external_document = fh.read()
        else:
            print("{}: Missing input file {}".format(path,external))
        start = match.start()
        end = match.end()
        try:
            if text[start-1]!='\n':
                external_document = '\n' + external_document
        except:
            pass
        try:
            if text[end]!='\n':
                external_document += '\n'
        except:
            external_document += '\n'
        text = text.replace(match.group(0),external_document)
    text = remove_comments(text)
    return text


def demacro_file(path):
    start_time = time.time()
    text = load_inputs(path)
    # print("Inputs document")
    # print(text)
    # Read in macro statements
    macro_types = ['\\newcommand','\\def']
    macrodict = {}
    for match in re.finditer(def_pattern,text):
        new_macro = macro()
        new_macro.load_def(match,text[match.end():])
        macro_def = new_macro.definition
        macro_name = re.escape(new_macro.name)
        if re.search(macro_name+r'(?![\w\*@])',macro_def):
            print("{}: Recursive macros detected: aborting2".format(path))
            return("")
        for macro_type in macro_types:
            if re.search(re.escape(macro_type)+r'(?![\w\*@])',macro_def):
                print("{}: Nested macros detected: aborting3".format(path))
                return("")
        macrodict[new_macro.name]=new_macro
        # text = text.replace(new_macro.macro_text(),"")
    for match in re.finditer(math_pattern,text):
        new_macro = macro()
        new_macro.load_mathoperator(text[match.end():],match.group(0))
        macro_def = new_macro.definition
        macro_name = re.escape(new_macro.name)
        if re.search(macro_name+r'(?![\w\*@])',macro_def):
            print("{}: Recursive macros detected: aborting4".format(path))
            return("")
        for macro_type in macro_types:
            if re.search(re.escape(macro_type)+r'(?![\w\*@])',macro_def):
                print("{}: Nested macros detected: aborting5".format(path))
                return("")
        macrodict[new_macro.name]=new_macro
        # text = text.replace(new_macro.macro_text(),"")
    for match in re.finditer(newcommand_pattern,text):
        new_macro = macro()
        new_macro.load_newcommand(text[match.start():])
        macro_def = new_macro.definition
        macro_name = re.escape(new_macro.name)
        if re.search(macro_name+r'(?![\w\*@])',macro_def):
            print("{}: Recursive macros detected: aborting6".format(path))
            print(macro_name)
            return("")
        for macro_type in macro_types:
            if re.search(re.escape(macro_type)+r'(?![\w\*@])',macro_def):
                print(macro_def)
                print("{}: Nested macros detected: aborting7".format(path))
                return("")
        macrodict[new_macro.name]=new_macro
        # text = text.replace(new_macro.macro_text(),"")
    nameset = set(macrodict.keys())
    if len(macrodict)==0:
        return text
    changed = True
    for item in macrodict:
        text = text.replace(macrodict[item].macro_text(),"")
    while changed:
        for item in macrodict:
            while(True):
                tomatch = re.escape(macrodict[item].name)
                # print("Search token: {}".format(tomatch))
                try:
                    match = re.search(tomatch+r'(?=[^\w\@\*])',text)
                except:
                    ValueError("TOMATCH: {}".format(tomatch))
                if not match:
                    changed = False
                    break
                # print(match.group(0))
                # print(match.start())
                index = match.start()
                before, expression = text[:index], text[index:]
                try:
                    substituted, after = macrodict[item].parse_expression(expression)
                except Exception as inst:
                    print("Error: failure to parse expression {}".format(
                    macrodict[item].name
                    ))
                    print(str(inst))
                    return("")
                merging = []
                merging.append(before)
                if before[-1]=='\n':
                    merging.append('')
                else:
                    merging.append('\n')
                merging.append(substituted)
                if len(after)>0:
                    if after[0]=='\n':
                        merging.append('')
                else:
                    merging.append('\n')
                merging.append(after)
                text = ''.join(merging)
                current_time = time.time()
                if current_time > start_time + timeout:
                    print("{}: Timed out".format(path))
                    return("")
                # print("NEW DOC LENGTH: {}".format(len(text)))
    text = re.sub(r'\n{3,}','\n\n',text)
    verbose("{}: COMPLETE".format(path))
    return text

def demacro_folder(path):
    main = find_main_file(path)
    if not main:
        print("{}: Main file not found".format(path))
        return
    # print(main)
    new_text = demacro_file(main)
    if not new_text:
        print("{}: returned blank document".format(main))
    else:
        print("{}: COMPLETE".format(main))
    return new_text

with open('macroexamples.tex','r') as fh:
    origtext = fh.read()


def mapped(folder):
    global outdirectory
    outdirectory = os.path.normpath(outdirectory)
    print(folder)
    new_text = demacro_folder(folder)
    new_name = os.path.split(os.path.normpath(folder))[1]
    if(new_text):
        with open(outdirectory+'/'+new_name+'.tex','w') as fh:
            fh.write(new_text)
    else:
        mainfile =  find_main_file(folder)
        if mainfile:
            text = load_inputs(mainfile)
            filename = os.path.basename(mainfile)
            with open('/media/jay/Data/ml_debug/'+filename,'w') as fh:
                fh.write(text)

def untarballs(folder,dest=''):
    if not dest:
        dest = folder
    validate_folder(dest)
    for fname in next(os.walk(folder))[2]:
        if fname.endswith("tar.gz"):
            tar = tarfile.open(os.path.join(folder,fname),"r:gz")
            tar.extractall(dest)
            tar.close()

def untar(archive):
    tar = tarfile.open(archive,"r:")
    tar.extractall()
    tar.close()



def main():
    parser = argparse.ArgumentParser(description='Expands LaTeX macros')
    parser.add_argument('input', help='Input file/directory')
    parser.add_argument('output', help='Ouptut file/directory')
    parser.add_argument('-d', '--directory', action='store_true',
    help='Indicates that input & output are dictories')
    parser.add_argument('-v', '--verbose', action='store_true',
    help='Enable verbose output')
    parser.add_argument('-k','--keep', action='store_true',
    help='Keeps untarred directories in output directory')
    parser.add_argument('-o', '--oldConvention', action='store_true',
    help='use this flag when applying demacro to submissions before 04/2007')
    args = parser.parse_args()
    pool = mp.Pool(mp.cpu_count())
    root, folders, files = next(os.walk(args.input))
    folderlist = [os.path.join(root, foldername) for foldername in folders]
    main_files = pool.map(find_main_file,folderlist)
    pool.map(find_macros,folderlist)
    pool.close()
    pool.join()
    return 0

if __name__=='__main__':
    main()
