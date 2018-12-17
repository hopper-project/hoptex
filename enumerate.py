"""Script for the enumeration of inline display mode math.
Generates an output tsv of the format: EQ#Q masked_equation"""
import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
import time
from multiprocessing import Manager
import multiprocessing as mp
from glob import glob
import shutil
import gc
from collections import defaultdict
import query_sql as qs
import tsv_to_sql as t2s

# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"
balign = "\\begin{align}"
ealign = "\\end{align}"


#TODO: enumerate_docs
'''
def substitute_eqid(filename):
    """Substitutes equations in document with their respective inline
    equations"""
    global eqdict
    global docpath
    global inline
    no_math = True
    with open(filename,mode='r',encoding='latin-1') as fh:
        text = fh.read()
    text = clean_inline_math(text)
    if(inline):
        textlist = grab_inline_math(text,split=True)
        for i, x in enumerate(textlist):
            if x in eqdict:
                textlist[i] = eqdict[x]
                no_math = False
        if no_math:
            print("{}: no inline math".format(filename))
            return
        newtext = ''.join(textlist)
    else:
        # math = grab_math(text)
        for equation in grab_math(text):
            flat_eq = flatten_equation(equation)
            if flat_eq in eqdict:
                text = text.replace(equation,eqdict[flat_eq])
            elif equation in eqdict:
                text = text.replace(equation,eqdict[equation])
            else:
                for expr in to_remove:
                    if re.search(expr,equation):
                        print("Enumeration error: {} Multiline".format(filename))
                        print(equation)
                        count += 1
                        break
                else:
                    print("Enumeration error: {}: Single line".format(filename))
                    print(equation)
                    count += 1
        newtext = text
    if docpath:
        filename = os.path.join(docpath,os.path.basename(filename))
    with open(filename,mode='w',encoding='utf-8') as fh:
        fh.write(newtext)
'''

def grab_eqs_and_filename(filename):
    return((filename,grab_math_from_file(filename)))

def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory",help="Path to directory of .tex files")
    #parser.add_argument("out_tsv",help="Path to output tsv file")
    parser.add_argument("--parent", action="store_true", help="Set to true if this is a folder of folders of .tex files")
    parser.add_argument("--initial", action="store_false", help="Use flag for initial batch processing")
    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    #out_tsv = os.path.abspath(args.out_tsv)
    parent = args.parent
    initial = args.initial
    tex_files = []
    unique_eqs = {}
    unique_meqs = {}
    doc_list = defaultdict(set)
    print("Starting timer...")
    start = time.time()

    print("Seeking .tex files...")
    # if this is a parent directory of several folders of .tex files
    if(parent):
        folderlist = next(os.walk(directory))[1]
        for subfolder in folderlist:
            print("Finding .tex files in {}".format(subfolder))
            current_dir = os.path.join(directory,subfolder)
            tex_files += gettexfiles(current_dir)
    else:
        tex_files = gettexfiles(directory)
    print("{} files found".format(len(tex_files)))

    # print("{} seconds".format(int(time.time()-start)))
    pool = mp.Pool(processes=mp.cpu_count())
    print("Grabbing math from files...")

    if initial:
        eqcount = 0
        meqcount = 0
    else:
        # get the next available eqid
        eqcount, meqcount = qs.get_next()
    all_math = pool.imap(grab_math_from_file,tex_files)
    for document_equations in all_math:
        document_name = document_equations[0].rstrip('.tex')
        equation_list = document_equations[1]
        for equation in equation_list:
            std_eq = standardize_equation(equation)
            # removed delimiters
            snt_eq = sanitize_equation(equation)
            # removed environment-specific tags
            flt_eq = flatten_equation(equation)
            # standardized, no whitespace
            for expr in cap_expr_list:
                match = re.match(expr,equation)
                if match:
                    if expr in multiline_list:
                        split_eqs = split_multiline(equation)
                        sub_ids = []
                        for sub_eq in split_eqs:
                            sub_eq = remove_whitespace(sanitize_equation(sub_eq,complete=True))
                            if sub_eq not in unique_eqs:
                                if not initial:
                                    result = qs.query_sql(mask(beq+sub_eq+eeq),document_name)
                                    if result == '':
                                        eqid = "EQDS"+str(eqcount)+"Q"
                                        eqcount += 1
                                    else:
                                        eqid = result
                                else:
                                    eqid = "EQDS"+str(eqcount)+"Q"
                                    eqcount += 1
                                unique_eqs[sub_eq] = (eqid,beq+sub_eq+eeq,1)
                            else: # increment freq count
                                prev = unique_eqs[sub_eq]
                                unique_eqs[sub_eq] = (prev[0], prev[1], prev[2]+1)
                            doc_list[sub_eq].add(document_name)
                            sub_ids.append(unique_eqs[sub_eq][0].rstrip('_F'))
                        if equation not in unique_meqs:
                            if not initial:
                                result = qs.query_sql(mask(equation),document_name)
                                if result == '':
                                    eqid = "EQDM"+str(meqcount)+"Q"
                                    meqcount += 1
                                else:
                                    eqid = result
                            else:
                                eqid = "EQDM"+str(meqcount)+"Q"
                                meqcount += 1
                            unique_meqs[equation] = (eqid,",".join(sub_ids),equation, 1)
                        else:
                            prev = unique_meqs[equation]
                            unique_meqs[equation] = (prev[0], prev[1], prev[2], prev[3]+1)
                        doc_list[equation].add(document_name)
                        break
                    else:
                        if flt_eq not in unique_eqs:
                            if not initial:
                                    result = qs.query_sql(mask(beq+std_eq+eeq),document_name)
                                    if result == '':
                                        eqid = "EQDS"+str(eqcount)+"Q"
                                        eqcount += 1
                                    else:
                                        eqid = result
                            else:
                                eqid = "EQDS"+str(eqcount)+"Q"
                                eqcount += 1
                            unique_eqs[flt_eq] = (eqid,beq+std_eq+eeq, 1)
                        else:
                            prev = unique_eqs[flt_eq]
                            unique_eqs[flt_eq] = (prev[0], prev[1], prev[2]+1)
                        doc_list[flt_eq].add(document_name)
                        break
    with open('4_cols.tsv',mode='w') as fh:
        for x in unique_eqs:
            EQID, eqtext, freq  = unique_eqs[x]
            docs = doc_list[x]
            fh.write(EQID+'\t'+mask(eqtext)+'\t'+repr(freq)+'\t'+','.join(docs)+'\n')
        for x in unique_meqs:
            EQID, sub_ids, eqtext, freq = unique_meqs[x]
            docs = doc_list[x]
            fh.write(EQID+'\t'+mask(eqtext)+'\t'+repr(freq)+'\t'+','.join(docs)+'\n')
    with open('sub_ids.tsv',mode='w') as fh:
        for x in unique_meqs:
            EQID, sub_ids, _, _ = unique_meqs[x]
            fh.write(EQID+'\t'+sub_ids+'\n')
    print("{} single line equations".format(len(unique_eqs)))
    print("{} multiline equations".format(len(unique_meqs)))
    # print("{} seconds".format(int(time.time()-start)))
    pool.close()
    pool.join()

    t2s.populate()

    #enumerate_docs


if __name__ == '__main__':
    main()

