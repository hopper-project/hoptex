"""Script for enumeration of inline math equations"""
import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
from collections import Counter
import time

def update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, eq):
    if document_name in tex_to_eqs_dict:
        eqs_list = tex_to_eqs_dict[document_name]
        if eq not in eqs_list:
            eqs_list.append(eq)
            tex_to_eqs_dict[document_name] = eqs_list

    else:
        tex_to_eqs_dict[document_name] = [eq]

    return tex_to_eqs_dict

def update_eqs_to_tex_dict(tex, eqs_to_tex_dict, eq):
    if eq in eqs_to_tex_dict:
        tex_list = eqs_to_tex_dict[eq]
        if tex not in tex_list:
            tex_list.append(tex)
            eqs_to_tex_dict[eq] = tex_list
    else:
        eqs_to_tex_dict[eq] = [tex]

    return eqs_to_tex_dict

def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory", help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    parser.add_argument("--xhtml", help="Path to directory of xhtml files")
    parser.add_argument("--tsv", help="TSV to continue building off of")
    parser.add_argument("--parent", action="store_true", help="Use if this is the parent directory of multiple .tex files")
    parser.add_argument("--tex_eqs", help="tex to eqs tsv to continue loading")
    parser.add_argument("--eqs_tex", help="eqs to tex tsv to continue loading")
    args = parser.parse_args()
    xhtml = args.xhtml
    outfile = args.outfile
    parent = args.parent
    directory = os.path.join(os.path.abspath(args.directory),'')
    tsv = args.tsv
    tex_eqs = args.tex_eqs
    eqs_tex = args.eqs_tex
    unique_eqs = {}
    tex_to_eqs_dict={}
    eqs_to_tex_dict={}
    if tsv:
        print("Loading equations")
        with open(tsv,mode='r',encoding='latin-1') as fh:
            for line in fh:
                line = line.strip('\n')
                linesplit = line.split('\t')
                eqid = linesplit[0]
                text = unmask(linesplit[1]).strip()
                freq = int(linesplit[2])
                unique_eqs[text] = (eqid, freq)
    if(tex_eqs):
        print("Loading tex to eqs tsv...")
        with open(tex_eqs,mode='r') as fh:
            for line in fh:
                line = line.strip('\n')
                linesplit = line.split('\t')
                tex_name = linesplit[0]
                tex_to_eqs_dict[tex_name] = linesplit[1:]
    if(eqs_tex):
        print("Loading eqs to tex tsv...")
        with open(eqs_tex,mode='r') as fh:
            for line in fh:
                line = line.strip('\n')
                linesplit = line.split('\t')
                eqid = linesplit[0]
                eqs_to_tex_dict[eqid] = linesplit[1:]
    if(parent):
        folderlist = next(os.walk(directory))[1]
        matches = []
        for subfolder in folderlist:
            print("Finding .tex files in {}".format(subfolder))
            current_dir = os.path.join(directory,subfolder)
            matches += gettexfiles(current_dir)
    else:
        matches = gettexfiles(directory)
    print("Found {} files".format(len(matches)))
    if(xhtml):
        pass
    pool = mp.Pool(processes=mp.cpu_count())
    print("Grabbing math from files...")
    eqcount = 0
    filecount = 0
    math_equations = pool.imap(grab_inline_math_from_file,matches)
    with open(outfile,'w') as fh:
        # doceqs = (document name, list of eqs)
        for doceqs in math_equations:
            document_name = doceqs[0].rstrip('.tex')
            equation_list = doceqs[1]
            for equation in equation_list:
                if equation not in unique_eqs:
                    tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, "EQIX"+str(eqcount)+"Q")
                    eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict, "EQIX"+str(eqcount)+"Q")
                    unique_eqs[equation] = ("EQIX" + str(eqcount) + "Q", 1)
                    eqcount += 1
                else:
                    old_info = unique_eqs[equation]
                    tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, old_info[0])
                    eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict, old_info[0])
                    unique_eqs[equation] = (old_info[0],old_info[1]+1)
            filecount += 1
        for x in unique_eqs:
            fh.write(unique_eqs[x][0]+'\t'+mask(x)+'\t'+repr(unique_eqs[x][1])+'\t'+','.join(eqs_to_tex_dict[unique_eqs[x][0]])+'\n')
    with open(tex_eqs,mode='w') as fh:
        for document_name in tex_to_eqs_dict:
            eqs_list = tex_to_eqs_dict[document_name]
            fh.write(document_name+'\t'+'\t'.join(eqs_list)+'\n')
    with open(eqs_tex,mode='w') as fh:
        for eqid in eqs_to_tex_dict:
            tex_list = eqs_to_tex_dict[eqid]
            fh.write(eqid+'\t'+'\t'.join(tex_list)+'\n')
    print("{} unique equations".format(len(unique_eqs)))
    print("{} new equations".format(eqcount))

if __name__=='__main__':
    main()
