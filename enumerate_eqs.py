"""Script for the enumeration of inline display mode math.
Generates an output tsv of the format: EQ#Q masked_equation"""
import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
import time

# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"
balign = "\\begin{align}"
ealign = "\\end{align}"

def grab_eqs_and_filename(filename):
    return((filename,grab_math_from_file(filename)))

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
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    parser.add_argument("--xhtml", help="Path to directory of xhtml files")
    parser.add_argument("--tsv", help="Path to tsv to continue loading ")
    parser.add_argument("--parent", action="store_true", help="Set to true if this is a folder of folders of .tex files")
    parser.add_argument("--tex_eqs", help="tex to eqs tsv to continue loading")
    parser.add_argument("--eqs_tex", help="eqs to tex tsv to continue loading")
    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    outpath = os.path.abspath(args.outfile)
    parent = args.parent
    tsv = args.tsv
    xhtml = False
    tex_eqs = args.tex_eqs
    eqs_tex = args.eqs_tex
    tsv_write_mode = 'w'
    if(args.xhtml):
        xhtml = os.path.abspath(args.xhtml)
    matches = []
    unique_eqs = {}
    unique_meqs = {}
    tex_to_eqs_dict = {}
    eqs_to_tex_dict = {}
    print("Starting timer...")
    start = time.time()
    # 'resuming' a tsv
    # allows enumeration to continue from a previously written tsv
    # still writes the new tsv to the output destination
    if(tsv):
        print("Loading equations...")
        with open(tsv,mode='r',encoding='latin-1') as fh:
            for line in fh:
                line = line.strip('\n')
                linesplit = line.split('\t')
                eqid = linesplit[0]
                text = unmask(linesplit[1]).strip()
                freq = int(linesplit[2])
                unique_eqs[text] = (eqid, text, freq)
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
    print("Seeking .tex files...")
    # if this is a parent directory of several folders of .tex files
    if(parent):
        folderlist = next(os.walk(directory))[1]
        for subfolder in folderlist:
            print("Finding .tex files in {}".format(subfolder))
            current_dir = os.path.join(directory,subfolder)
            matches += gettexfiles(current_dir)
    else:
        matches = gettexfiles(directory)
    print("{} files found".format(len(matches)))
    # generate list of xhtml files, if we're given a folder to look in
    if(xhtml):
        xhtmlmatches = {}
        for root, directories, filenames in os.walk(xhtml):
            for filename in fnmatch.filter(filenames,'*.xhtml'):
                filename = os.path.join(root,filename)
                processedname = os.path.join(os.path.split(os.path.split(filename)[0])[1][:-10],os.path.splitext(os.path.split(filename)[1])[0])
                #note that the [:-10] is to remove '_converted' from the xhtml folder name
                #blah/astro-ph_converted/example.xhtml becomes astro-ph/example
                xhtmlmatches[processedname] = filename
        for filename in matches:
            mismatch = []
            match = []
            processedname = os.path.join(os.path.split(os.path.split(filename)[0])[1],os.path.splitext(os.path.split(filename)[1])[0])
            if processedname not in xhtmlmatches:
                mismatch.append(processedname)
            else:
                match.append(processedname)
    # print("{} seconds".format(int(time.time()-start)))
    pool = mp.Pool(processes=mp.cpu_count())
    print("Grabbing math from files...")
    eqcount = len(unique_eqs)
    meqcount = 0
    # code for creating the 3-column tsv with matching xhtml docs
    if(xhtml):
        all_math = pool.imap(grab_eqs_and_filename,matches)
        for tup in all_math:
            xhtmlMath = False
            xhtmlMathMatch = False
            processedname = os.path.join(os.path.split(os.path.split(filename)[0])[1],os.path.splitext(os.path.split(filename)[1])[0])
            if processedname in xhtmlmatches:
                xhtmlMath = True
                with open(xhtmlmatches[processedname],'r') as fh:
                    document = fh.read()
                xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>',document)
                if len(xhtml_equations)==len(tup[1]):
                    xhtmlMathMatch = True
            for i, equation in enumerate(tup[1]):
                if equation not in unique_eqs:
                    if xhtmlMathMatch:
                        unique_eqs[equation] = ("EQ" + str(eqcount) + "Q",xhtml_equations[i], 1)
                    else:
                        unique_eqs[equation] = ("EQ" + str(eqcount) + "Q","", 1)
                    eqcount+=1
                else: # increment freq count
                    old_info = unique_eqs[equation]
                    unique_eqs[equation] = (old_info[0], old_info[1], old_info[2]+1)
        pool.close()
        pool.join()
        print("WRITING TO FILE: {}".format(outpath))
        with open(outpath,mode='w') as fh:
            for x in unique_eqs:
                fh.write(unique_eqs[x][0]+'\t'+repr(x)[1:-1].replace("\t","\\t")+'\t'+repr(unique_eqs[x][1])[1:-1].replace("\t","\\t")+'\t'+repr(unique_eqs[x][2])+'\n')
    else:
        all_math = pool.imap(grab_math_from_file,matches)
        # document_equations = (document name, list of eqs)
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
                                # check if sub_eq in tex_to_eqs_dict
                                if sub_eq not in unique_eqs:
                                    tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, "EQDS"+str(eqcount)+"Q")
                                    eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict, "EQDS"+str(eqcount)+"Q")
                                    unique_eqs[sub_eq] = ("EQDS"+str(eqcount)+"Q",beq+sub_eq+eeq,1)
                                    eqcount += 1
                                else: # increment freq count
                                    old_info = unique_eqs[sub_eq]
                                    tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict,old_info[0])
                                    eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict,old_info[0])
                                    unique_eqs[sub_eq] = (old_info[0], old_info[1], old_info[2]+1)
                                sub_ids.append(unique_eqs[sub_eq][0])
                            if equation not in unique_meqs:
                                tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, "EQDM"+str(meqcount)+"Q")
                                eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict,"EQDM"+str(meqcount)+"Q")
                                unique_meqs[equation] = ("EQDM"+str(meqcount)+"Q",",".join(sub_ids),equation,1)
                                meqcount += 1
                            else:
                                old_info = unique_meqs[equation]
                                tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict,old_info[0])
                                eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict,old_info[0])
                                unique_meqs[equation] = (old_info[0], old_info[1], old_info[2], old_info[3]+1)
                            break
                        else:
                            # check if sub_eq in tex_to_eqs_dict
                            if flt_eq not in unique_eqs:
                                tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, "EQDS"+str(eqcount)+"Q")
                                eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict, "EQDS"+str(eqcount)+"Q")
                                unique_eqs[flt_eq] = ("EQDS"+str(eqcount)+"Q",beq+std_eq+eeq,1)
                                eqcount += 1
                            else:
                                old_info = unique_eqs[flt_eq]
                                tex_to_eqs_dict = update_tex_to_eqs_dict(document_name, tex_to_eqs_dict, old_info[0])
                                eqs_to_tex_dict = update_eqs_to_tex_dict(document_name, eqs_to_tex_dict,old_info[0])
                                unique_eqs[flt_eq] = (old_info[0], old_info[1], old_info[2]+1)
                            break
        with open(outpath,mode='w') as fh:
            for x in unique_eqs:
                EQID, eqtext, freq = unique_eqs[x]
                doc_list = eqs_to_tex_dict[EQID]
                fh.write(EQID+'\t'+mask(eqtext)+'\t'+repr(freq)+'\t'+','.join(doc_list)+'\n')
            for x in unique_meqs:
                EQID, sub_ids, eqtext, freq = unique_meqs[x]
                fh.write(EQID+'\t'+mask(eqtext)+'\t'+repr(freq)+'\t'+','.join(doc_list)+'\n')
                #fh.write(EQID+'\t'+sub_ids+'\t'+mask(eqtext)+'\t'+repr(freq)+'\t'+','.join(doc_list)+'\n')
        with open(tex_eqs,mode='w') as fh:
            for document_name in tex_to_eqs_dict:
                eqs_list = tex_to_eqs_dict[document_name]
                fh.write(document_name+'\t'+'\t'.join(eqs_list)+'\n')
        with open(eqs_tex,mode='w') as fh:
            for eqid in eqs_to_tex_dict:
                tex_list = eqs_to_tex_dict[eqid]
                fh.write(eqid+'\t'+'\t'.join(tex_list)+'\n')
    print("{} single line equations".format(len(unique_eqs)))
    print("{} multiline equations".format(len(unique_meqs)))
    # print("{} seconds".format(int(time.time()-start)))
    pool.close()
    pool.join()

if __name__ == '__main__':
    main()
