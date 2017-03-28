"""Module for removing macros from LaTeX documents

Parse macros in LaTeX source code. Supported macros include:
    - newcommand/renewcommand(*)
    - DeclareMathOperator
    - def
    - input
"""

import re
import os
import time
import sys
import tarfile
import multiprocessing as mp
import shutil
import argparse

from core.funcs import *
global diag_message
global rcp
global output_path
global debug
global debug_path
global timeout

diag_message = False
debug = False
debug_path = './debug/'
timeout = 240

#Regex pattern for seeking & retrieving args & separators for def
# def_pattern = r0+r1+r2+r3+r4+r5+r6+r7+r8+r9

# A truly monstrous regular expression, from a less civilized age

def_pattern = r'(?s)\\(?:e|g)?def\s*(?P<name>\\[A-Za-z@\*]+|\\.)\s*(?:(?P<sep1>[^\{#]*)(?P<arg1>#1)(?P<sep2>[^\{#]*)(?:(?P<arg2>#2)(?P<sep3>[^\{#]*)(?:(?P<arg3>#3)(?P<sep4>[^\{#]*)(?:(?P<arg4>#4)(?P<sep5>[^\{#]*)(?:(?P<arg5>#5)(?P<sep6>[^\{#]*)(?:(?P<arg6>#6)(?P<sep7>[^\{#]*)(?:(?P<arg7>#7)(?P<sep8>[^\{#]*)(?:(?P<arg8>#8)(?P<sep9>[^\{#]*)(?:(?P<arg9>#9)(?P<sep10>[^\{#]*))?)?)?)?)?)?)?)?)?(?=\{)'

math_pattern = r"\\DeclareMathOperator\*?"

def_token = r'\\g?def(?![A-Za-z@])'

input_pattern = r'\\input\s*\{\s*([^\s\\]+)\}|\\input(?![A-Za-z@])\s*([^\s\\]+)'

newcommand_pattern = r'\\newcommand\*?'

renewcommand_pattern = r'\\renewcommand\*?'

search_pattern = r'(?P<def>'+def_pattern+')'+r'|(?P<newcommand>'+newcommand_pattern+r')'+\
    r'|(?P<renewcommand>'+renewcommand_pattern+r')'+r'|(?P<mathoperator>'+math_pattern+r')'

macro_pattern= '|'.join([def_token,newcommand_pattern,renewcommand_pattern,math_pattern])

begin_document = r'\\begin\{document\}'

nested_arg_pattern = r'(?s)(\\#|[^\\])(#{2,})([1-9])'

arg_pattern = r'(?s)(?<![#\\])#'

single_token_group = r'(?<!\\)\{\s*(\\[A-Za-z\@\*]+)(?<!\\)\s*\}'

delim_token_group = r'(?<!\\)\{\s*((?:\\begin|\\end|\\\[|\\\])(?:\{[A-Za-z\@\*]+\})?|\${1,2}|\\\[|\\\])(?<!\\)\s*\}'

macro_token_group = r'(?<!\\)\{\s*(\\((?:re)?newcommand\*?)|\\g?def|\\DeclareMathOperator\*?)(?<!\\)\s*\}'

isundefined_pattern = r'\\isundefined\s*\{\s*(\\[A-Za-z\@\*]*)\s*\}'

"""
A lot of the code below is necessary because Python has been taking 5 years and counting
to put the superior 'regex' module from PyPI into stdlib
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
    if len(stack)==0:
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
    backslash_count = 0
    if text[0]=='{':
        stack = []
        for i, character in enumerate(text):
            group.append(character)
            if character=='\\':
                backslash_count+=1
                continue
            elif character=='{':
                if backslash_count%2==0:
                    stack.append(character)
            elif character=='}':
                if backslash_count%2==0:
                    stack.pop()
                if len(stack)==0:
                    break
            backslash_count=0
        return(''.join(group),text[i+1:])
    else:
        return('',text)

def take_param(text):
    group = []
    backslash_count = 0
    if text[0]=='[':
        stack = []
        for i, character in enumerate(text):
            group.append(character)
            if character=='\\':
                backslash_count+=1
                continue
            elif character=='[':
                if backslash_count%2==0:
                    stack.append(character)
            elif character==']':
                if backslash_count%2==0:
                    stack.pop()
                if len(stack)==0:
                    break
            backslash_count=0
        return(''.join(group),text[i+1:])
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
        if not re.match(r'[A-Za-z@\*]',text[1]):
            token.append(text[1])
            return (''.join(token),text[2:])
        for i, character in enumerate(text[1:]):
            if re.match(r'[A-Za-z@\*]',character):
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

def escape(text):
    return text.replace("\\","\\\\")

def is_group(text):
    stack = []
    backslash_count = 0
    if len(text)==0:
        return False
    if text[0]!='{':
        return False
    for i, character in enumerate(text):
        if i>0:
            if len(stack)==0:
                return False
        if character=='{':
            if backslash_count%2==0:
                stack.append('{')
            backslash_count = 0
        elif character=='}':
            if backslash_count%2==0:
                if len(stack)>0:
                    stack.pop()
                else:
                    return False
            backslash_count = 0
        elif character=='\\':
            backslash_count += 1
        else:
            backslash_count = 0
    if len(stack)==0:
        return True
    return False

def reduce_group(text):
    while is_group(text):
        text = text[1:-1].strip()
    return '{' + text + '}'

def extract_group(text):
    while is_group(text):
        text = text[1:-1].strip()
    return text

def enclose_in_group(text):
    if is_group(text):
        return text
    return '{'+text+'}'

def num_valid(items):
    val = 0
    for item in items:
        if item:
            val += 1
    return val

def reduce_arguments(text):
    match = re.search(nested_arg_pattern,text)
    new = []
    while match:
        new.append(text[:match.start()])
        match_text = match.group(0)
        pounds = match.group(1)
        new_text = pounds[:int(len(pounds)/2)] + match.group(2)
        new.append(new_text)
        text = text[match.end():]
        match = re.search(nested_arg_pattern,text)
    new.append(text)
    return(''.join(new))

#Parsing sequences
newcommand_sequence = [take_token, take_whitespace, take_general,
                        take_whitespace, take_param, take_whitespace,
                        take_param, take_whitespace, take_general]

math_operator_sequence = [take_whitespace,take_general,
                            take_whitespace,take_general]


def_input_sequence = [take_token,take_whitespace]

renewcommand_sequence = newcommand_sequence

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
        self.valid = True
        self.contains_macro_defs = False

    def macro_text(self):
        global verbose
        verbose("Replace: {}".format(self.text))
        return self.text

    def load_def(self, match_obj,text):
        #copies over to avoid mutating the original def list
        global verbose
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
        match_pattern = re.escape(self.name)
        if self.name == '':
            self.valid = False
            return
        if re.search(match_pattern+r'(?![A-Za-z\@])',self.definition):
            self.definition = ''
            verbose("Encountered nested definition - erasing1")
            verbose(self.definition)
            verbose(self.name)
        # if re.search(r'(?<!\\)#{2,}[0-9]',self.definition):
        #     print("Nested macros detected erasing")
        #     self.definition = ''
        self.definition = re.sub(re.escape(self.name)+r'(?![A-Za-z\@\*])','',self.definition)
        if re.search(macro_pattern,self.definition):
            self.contains_macro_defs = True
        verbose("Loading def")
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
        self.definition = "\\operatorname"+self.asterisk+self.arg2
        verbose("Loading Mathoperator")
        verbose(self.arg1)
        verbose(self.arg2)
        verbose("End mathoperator")

    def load_newcommand(self,text):
        try:
            results = parse(text,newcommand_sequence)[0]
        except:
            self.valid = False
            return
        self.text = ''.join(results)
        self.type = results[0]
        if self.type[-1]=='*':
            self.asterisk = '*'
            self.type = self.type[:-1]
        self.name = extract_group(results[2])
        self.arg_count = results[4]
        self.default = results[6]
        self.definition = results[8]
        if self.name == '':
            self.valid = False
            return
        if self.arg_count:
            try:
                self.arg_count = int(self.arg_count[1:-1])
            except:
                match = re.search(r'[0-9]',self.arg_count)
                if match:
                    self.arg_count = int(match.group(0))
                else:
                    print(self.arg_count)
                    ValueError("Error parsing argcount: {}".format(self.arg_count))
        else:
            self.arg_count = 0
        self.definition = re.sub(re.escape(self.name)+r'(?![A-Za-z\@\*])','',self.definition)
        if re.search(macro_pattern,self.definition):
            self.contains_macro_defs = True
        verbose("Loading newcommand: {}".format(self.name))
        verbose("Default parameter: {}".format(self.default))
        verbose("{} args".format(self.arg_count))
        verbose(self.definition)
        verbose("End newcommand")

    def load_renewcommand(self,text):
        try:
            results = parse(text,newcommand_sequence)[0]
        except:
            self.valid = False
            return
        self.text = ''.join(results)
        self.type = results[0]
        if self.type[-1]=='*':
            self.asterisk = '*'
            self.type = self.type[:-1]
        self.name = extract_group(results[2])
        if self.name == '':
            self.valid = False
            return
        self.arg_count = results[4]
        self.default = results[6]
        self.definition = results[8]
        if self.arg_count:
            try:
                self.arg_count = int(self.arg_count[1:-1])
            except:
                match = re.search(r'[0-9]',self.arg_count)
                if match:
                    self.arg_count = int(match.group(0))
                else:
                    print(self.arg_count)
                    ValueError("Error parsing argcount: {}".format(self.arg_count))
        else:
            self.arg_count = 0
        if re.search(macro_pattern,self.definition):
            self.contains_macro_defs = True
        verbose("Loading renewcommand: {}".format(self.name))
        verbose("Default parameter: {}".format(self.default))
        verbose("{} args".format(self.arg_count))
        verbose(self.definition)
        verbose("End renewcommand")
        self.definition = re.sub(re.escape(self.name)+r'(?![A-Za-z\@\*])','',self.definition)

    def substitute_arguments(self, arglist, default_arg=''):
        """Accepts a list of the values of args, returns definition with args"""
        text = self.definition
        text = re.sub(r'(\\#)#','\1 #',text)
        if self.type=='\\def':
            for i, arg in enumerate(arglist):
                verbose("definition")
                verbose(text)
                verbose("Passed argument:")
                verbose(arg)
                verbose("Argument index: {}".format(i))
                new_pattern = arg_pattern+str(i+1)
                text = re.sub(new_pattern,escape(arg),text)
                # text = text.replace('#'+str(i+1),arg)
            text = reduce_arguments(text)
            return(text)
        elif self.type=='\\newcommand' or self.type=='\\newcommand*':
            verbose("Newcommand arglist: {}".format(arglist))
            if self.default:
                if default_arg:
                    verbose("Replacing with new default: {}".format(default_arg))
                    text = re.sub(arg_pattern+'1',escape(default_arg[1:-1]),
                    text)
                else:
                    verbose("Replacing with original default")
                    text = re.sub(arg_pattern+'1',escape(self.default[1:-1]),
                    text)
                for i, arg in enumerate(arglist):
                    text = re.sub(arg_pattern+str(i+2),escape(arg),text)
                text = reduce_arguments(text)
                return text
            else:
                for i, arg in enumerate(arglist):
                    text = re.sub(arg_pattern+str(i+1),escape(arg),text)
                    # text = text.replace('#'+str(i+1),arg)
                text = reduce_arguments(text)
                return text
        elif self.type=='\\renewcommand' or self.type=='\\renewcommand*':
            verbose("Renewcommand arglist: {}".format(arglist))
            if self.default:
                if default_arg:
                    verbose("Replacing with new default")
                    text = re.sub(arg_pattern+'1',escape(default_arg[1:-1]),
                    text)
                    # text = text.replace('#1',default_arg[1:-1])
                else:
                    verbose("Replacing with original default")
                    text = re.sub(arg_pattern+'1',escape(self.default[1:-1]),text)
                    # text = text.replace('#1',self.default[1:-1])
                for i, arg in enumerate(arglist):
                    text = re.sub(arg_pattern+str(i+2),escape(arg),text)
                    # text = text.replace('#'+str(i+2),arg)
                text = reduce_arguments(text)
                return text
            else:
                for i, arg in enumerate(arglist):
                    text = re.sub(arg_pattern+str(i+1),escape(arg),text)
                    # text = text.replace('#'+str(i+1),arg)
                text = reduce_arguments(text)
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
                verbose("ERROR: MISMATCHED TOKEN")
                verbose("EXPECTED: {}, MATCHED: {}DELIM".format(self.name,a[0]))
                Exception("Parsing failed")
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
            verbose(self.name)
            a, b = take_token(text)
            if self.arg_count == 0:
                return(self.definition,b)
            a, b = take_whitespace(b)
            default, b = take_param(b)
            a, b = take_whitespace(b)
            num_args = self.arg_count
            if default:
                verbose("NEW DEFAULT: {}".format(default))
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
            if self.default:
                num_args -= 1
            verbose("argument count: {}".format(self.arg_count))
            parsing = [take_general,take_whitespace]*(num_args-1)
            parsing.append(take_general)
            results, b = parse(b,parsing)
            results = [results[x] for x in range(0,len(results)+1,2)]
            verbose("results: {}".format(results))
            # verbose("Substituted",self.substitute_arguments(results,default))
            return(self.substitute_arguments(results,default),b)
        elif self.type == "\\DeclareMathOperator":
            a, b = take_token(text)
            return("\\operatorname"+self.asterisk+self.arg2,b)
        else:
            a, b = take_general(text)
            return("",b)

def find_main_file(folder):
    """Iterates over every document in the folder, and returns the path to the
    file with begin/end document statements
    """
    folder = os.path.abspath(folder)
    for root, dirs, files, in os.walk(folder):
        for filename in files:
            if os.path.splitext(filename)[1].lower()!='.tex':
                continue
            with open(os.path.join(root,filename),mode='r',encoding='latin-1') as fh:
                text = fh.read()
            if re.search(r'(?s)\\begin\{document\}.*?\\end\{document\}',text):
                return os.path.join(root,filename)
    return ""


def isundefined_sub(isundefined_dict,text):
    match = re.search(isundefined_pattern,text)
    while match:
        sub_string = 'isundefined'+str(len(isundefined_dict))
        isundefined_dict[sub_string] = match.group(0)
        text = text.replace(match.group(0),sub_string)
        match = re.search(isundefined_pattern,text)
    return text

def undo_isundefined_sub(isundefined_dict,text):
    for item in isundefined_dict:
        text = text.replace(item,isundefined_dict[item])
    return text

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

def sub_single_token_groups(text,token=''):
    while True:
        text, count = re.subn(delim_token_group,r'\1',text)
        if count==0:
            break
    if token:
        while True:
            text, count = re.subn('\{\s*('+re.escape(token)+')\s*\}',r'\1',text)
            if count==0:
                break
    return text

def substitute_macro_groups(text):
    while True:
        text, count = re.subn(macro_token_group,r'\1',text)
        if count==0:
            break
    return text

def load_and_remove_macros(macrodict,text):
    """Mutate macrodict to include new macros
    Return new_macros boolean & text"""
    new_macros = False
    match = re.search(search_pattern,text)
    text = substitute_macro_groups(text)
    while match:
        if match.group('def'):
            #def
            # match = re.search(def_pattern,text)
            if match==None:
                print("DEF MATCH NOT FOUND")
                print(text)
                print("END DEF MATCH")
                match = re.search(search_pattern,text)
            new_macro = macro()
            new_macro.load_def(match,text[match.end():])
            macro_def = new_macro.definition
            macro_name = re.escape(new_macro.name)
            if re.search(macro_name+r'(?![A-Za-z\*@])',macro_def):
                print("{}: Recursive macros detected: aborting2".format(macro_name))
                return(new_macros,"")
            if new_macro.valid:
                macrodict[new_macro.name]=new_macro
                new_macros = True
                text = text.replace(new_macro.macro_text(),"")
            else:
                print("{}: Invalid def macro, aborting".format(new_macro.name))
                return(new_macros,"")
        elif match.group('newcommand'):
            #newcommand(*)
            # match = re.search(newcommand_pattern,text)
            new_macro = macro()
            new_macro.load_newcommand(text[match.start():])
            # verbose("Loaded {}".format(new_macro.name))
            macro_def = new_macro.definition
            macro_name = re.escape(new_macro.name)
            if re.search(macro_name+r'(?![A-Za-z\*@])',macro_def):
                print("{}: Recursive macros detected: aborting6".format(new_macro.name))
                print(macro_name)
                return(new_macros,"")
            if new_macro.valid:
                macrodict[new_macro.name]=new_macro
                new_macros = True
                text = text.replace(new_macro.macro_text(),"")
            else:
                print("{}: Invalid newcommand macro, aborting".format(new_macro.name))
                return(new_macros,"")
        elif match.group('renewcommand'):
            #renewcommand(*)
            # match = re.search(renewcommand_pattern,text)
            new_macro = macro()
            new_macro.load_renewcommand(text[match.start():])
            macro_def = new_macro.definition
            macro_name = re.escape(new_macro.name)
            if re.search(macro_name+r'(?![A-Za-z\*@])',macro_def):
                print("{}: Recursive macros detected: aborting7".format(new_macro.name))
                print(macro_name)
                return(new_macros,"")
            if new_macro.valid:
                macrodict[new_macro.name]=new_macro
                new_macros = True
                text = text.replace(new_macro.macro_text(),"")
            else:
                print("{}: Invalid renewcommand macro".format(new_macro.name))
                return(new_macros,"")
        elif match.group('mathoperator'):
            #DeclareMathOperator
            # match = re.search(math_pattern,text)
            new_macro = macro()
            new_macro.load_mathoperator(text[match.end():],match.group(0))
            macro_def = new_macro.definition
            macro_name = re.escape(new_macro.name)
            if re.search(macro_name+r'(?![A-Za-z\*@])',macro_def):
                print("{}: Recursive macros detected: aborting4".format(new_macro.name))
                return(new_macros,"")
            if new_macro.valid:
                macrodict[new_macro.name]=new_macro
                text = text.replace(new_macro.macro_text(),"")
                new_macros = True
            else:
                print("{}: Invalid math macro, aborting.".format(new_macro.name))
                return(new_macros,"")
        match = re.search(search_pattern,text)
    return(new_macros,text)

def demacro_file(path):
    global diag_message
    global debug
    global timeout
    start_time = time.time()
    text = load_inputs(path)
    newlines  = len(re.findall(r'\n',text))
    if debug:
        timeout = 10000
    macrodict = {}
    new_macros = True
    changed = True
    macro_blacklist = set()
    try:
        new_macros, text = load_and_remove_macros(macrodict,text)
    except:
        print("{}: Error encountered when loading macros".format(path))
        return("")
    if len(macrodict)==0:
        return text
    isundefined_dict = {}
    text = isundefined_sub(isundefined_dict,text)
    while (new_macros or changed):
        new_macros = False
        changed = False
        substituted_macro_defs = False
        for item in macrodict:
            if item in macro_blacklist:
                continue
            text = sub_single_token_groups(text,item)
            substituted_macro_defs = False
            while(True):
                tomatch = re.escape(macrodict[item].name)
                try:
                    match = re.search(tomatch+r'(?![A-Za-z\@\*])',text)
                except:
                    ValueError("TOMATCH: {}".format(tomatch))
                if not match:
                    break
                changed = True
                if macrodict[item].arg_count==0:
                    verbose("Regex sub: {}".format(item))
                    escaped_name = re.escape(item)+r'(?![A-Za-z\@\*])'
                    macro_def = escape(reduce_arguments(macrodict[item].definition))
                    text = re.sub(escaped_name,macro_def,text)
                else:
                    index = match.start()
                    before, expression = text[:index], text[index:]
                    verbose("Substituting arguments")
                    try:
                        substituted, after = macrodict[item].parse_expression(expression)
                    except Exception as inst:
                        print("{}: Error: failure to parse expression {} - removing macro".format(
                        path,macrodict[item].name
                        ))
                        macro_blacklist.add(macrodict[item].name)
                        break
                    merging = []
                    merging.append(before)
                    if len(before)>0:
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
                if macrodict[item].contains_macro_defs:
                    substituted_macro_defs = True
                current_time = time.time()
                text = isundefined_sub(isundefined_dict,text)
                text = sub_single_token_groups(text)
                if current_time > start_time + timeout:
                    print("{}: Timed out ({} seconds)".format(path,int(current_time-start_time)))
                    return("")
                text = re.sub(r'\n{3,}','\n\n',text)
                verbose(len(text))
            init_length = len(macrodict)
            if substituted_macro_defs:
                verbose("Searching for new macros...")
                try:
                    new_macros, text = load_and_remove_macros(macrodict,text)
                except:
                    print("{}: Error encountered when loading macros".format(path))
                    return("")
                verbose("Finished searching")
            if new_macros or init_length != len(macrodict):
                break
    text = undo_isundefined_sub(isundefined_dict,text)
    text = re.sub(r'\n{3,}','\n\n',text)
    text = sub_single_token_groups(text)
    if not grab_body(text):
        print("{}: No body found".format(path))
        return("")
    return text

def demacro_archive(path):
    main = find_main_file(path)
    if not main:
        print("{}: Main file not found".format(path))
        return
    print("Starting: {}".format(main))
    new_text = demacro_file(main)
    if not new_text:
        print("{}: returned blank document".format(main))
    else:
        print("{}: COMPLETE".format(main))
    return new_text


def untarballs(folder,dest=''):
    if not dest:
        dest = folder
    else:
        validate_folder(dest)
    for fname in next(os.walk(folder))[2]:
        if fname.endswith("tar.gz"):
            try:
                tar = tarfile.open(os.path.join(folder,fname),"r:gz")
                tar.extractall(dest)
                tar.close()
            except Exception as inst:
                print("{}: Unable to extract".format(fname))
                print(inst)
    for fname in next(os.walk(dest))[2]:
        if fname.endswith(".tar.gz"):
            os.remove(os.path.join(folder,fname))

def untar(archive,dest=''):
    if not dest:
        dest = os.path.split(archive)[0]
    else:
        validate_folder(dest)
    try:
        tar = tarfile.open(archive,"r:")
        tar.extractall(path=dest)
        tar.close()
    except Exception as inst:
        print("{}: Extraction failed".format(archive))
        print(inst)

"""The following functions are all involved with the following pipeline:
    .tar->folder of .tar.gz -> folder of raw .tex directories"""

def untar_folder(folder,dest):
    """.tar->folder of .tar.gz"""
    if dest:
        validate_folder(dest)
    else:
        dest = folder
    for fname in next(os.walk(folder))[2]:
        if fname.endswith('.tar'):
            untar(os.path.join(folder,fname),dest)

def untarballs_folder(folder,dest=''):
    """folder of .tar.gz->folder of raw .tex dirs"""
    for fname in next(os.walk(folder))[1]:
        untarballs(os.path.join(folder,fname),dest)

def total_extract(archive,dest):
    """.tar->folder of raw .tex"""
    print("Extracting {}".format(archive))
    untar(archive,dest)
    fname = os.path.splitext(os.path.split(archive)[1])[0]
    untarballs(os.path.join(dest,fname))
    print("Extraction complete")

def total_extract_folder(folder,dest=''):
    """folder of tars.tar->folder of folders of raw .tex"""
    untar_folder(folder,dest)
    untarballs_folder(dest,'')


def demacro_mapped(folder):
    """Wrapper function for handling in/out paths & failed document output"""
    global output_path
    global debug_path
    output_path = os.path.normpath(output_path)
    new_text = demacro_archive(folder)
    new_name = os.path.split(os.path.normpath(folder))[1]
    if(new_text):
        with open(output_path+'/'+new_name+'.tex','w') as fh:
            fh.write(new_text)
    else:
        mainfile =  find_main_file(folder)
        if mainfile:
            text = load_inputs(mainfile)
            filename = os.path.basename(mainfile)
            with open(debug_path+new_name+'.tex','w') as fh:
                fh.write(text)

def demacro_folder(folder):
    """Demacro a folder of raw .tex directories"""
    global output_path
    global debug_path
    folder = os.path.abspath(folder)
    folders = next(os.walk(folder))[1]
    folderlist = [os.path.join(folder,item) for item in folders]
    pool = mp.Pool(mp.cpu_count())
    pool.map(demacro_mapped,folderlist)
    pool.close()
    pool.join()
    folders = next(os.walk(output_path))[1]
    outfolderlist = [os.path.join(output_path,item) for item in folders]
    for fname in outfolderlist:
        shutil.rmtree(fname,ignore_errors=True)

def demacro_and_untar(archive,dest):
    """Untar archive to folder & demacro. e.g. 1506.tar to example/1506 should
    just pass 'example' into dest"""
    global output_path
    global debug_path
    new_name = os.path.split(os.path.splitext(archive)[0])[1]
    output_path = os.path.join(dest,new_name)
    validate_folder(output_path)
    total_extract(archive,dest)
    demacro_folder(output_path)

def demacro_and_untar_folder(archive_folder,dest):
    """demacro_and_untar, but for a folder of .tar files"""
    global output_path
    global debug_path
    validate_folder(debug_path)
    validate_folder(dest)
    archive_list = [os.path.join(archive_folder,fname) for fname in next(os.walk(archive_folder))[2] if fname.endswith('.tar')]
    for archive in archive_list:
        demacro_and_untar(archive,dest)

def recombine_file(tex_folder_path,output_file):
    """Compiles the entire document into a single file,
    and writes to specified file"""
    text = load_inputs(find_main_file(tex_folder_path))
    with open(output_path,'w') as fh:
        fh.write(text)


def main():
    global debug
    global debug_path
    global diag_message
    global input_path
    global output_path
    global timeout
    global output_path
    parser = argparse.ArgumentParser(
    description='Expands LaTeX macros. Default: demacro a single folder of .tex files')
    parser.add_argument('input', help='Input file/directory')
    parser.add_argument('output', help='Output file/directory')
    parser.add_argument('--dtar', action='store_true',
    help='Indicate that input is a directory of .tar files')
    parser.add_argument('--dgz',action='store_true',
    help='Indicate that input is a directory of .tar.gz files')
    parser.add_argument('--verbose', action='store_true',
    help='Enable verbose output')
    parser.add_argument('--debug',help='Path to store failed files')
    parser.add_argument('--tar',action='store_true',
    help='Indicate that input is a single .tar file')
    parser.add_argument('--timeout',help='Declare custom timeout')
    parser.add_argument('--folder',action='store_true',
    help='Indicate that input is folder corresponding to a single .tex document')
    parser.add_argument('--file',action='store_true',
    help='Indicate that input is a single .tex file')
    parser.add_argument('--edgz',action='store_true',
    help='Indicate that folder contains extracted .tar.gz folders')
    # parser.add_argument('-o', '--oldConvention', action='store_true',
    # help='use this flag when applying demacro to submissions before 04/2007')
    args = parser.parse_args()
    input_path = args.input
    output_path = args.output
    if args.debug:
        debug_path = args.debug
    validate_folder(debug_path)
    validate_folder(output_path)
    if args.verbose:
        diag_message = True
    debug = False
    if not os.path.exists(input_path):
        ValueError("Input does not exist: {}".format(args.input))
    if args.timeout:
        timeout = int(args.timeout)
    if args.dtar:
        demacro_and_untar_folder(input_path,output_path)
    elif args.dgz:
        folder_name = os.path.basename(os.path.normpath(input_path))
        untarballs(input_path,os.path.join(output_path,folder_name))
        demacro_folder(os.path.join(output_path,folder_name))
    elif args.tar:
        demacro_and_untar(archive,output_path)
    elif args.folder:
        demacro_archive(input_path)
    elif args.file:
        text = demacro_file(input_path)
        with open(output_path,'w') as fh:
            fh.write(text)
    elif args.edgz:
        demacro_folder(input_path)
    else:
        text = demacro_file(input_path)
        print(text)

if sys.flags.interactive:
    pass
else:
    if __name__=='__main__':
        main()
