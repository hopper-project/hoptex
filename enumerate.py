"""Script for the enumeration of inline display mode math.
Generates an output tsv of the format: EQ#Q masked_equation"""
import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
import time
from collections import defaultdict

# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"
balign = "\\begin{align}"
ealign = "\\end{align}"

def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory", help="Path to directory of .tex files")
    parser.add_argument("--parent", action="store_true", help="Set to true if this is a folder of folders of .tex files")
    parser.add_argument("--initial", action="store_true", help="Use flag for initial batch processing")
    parser.add_argument("K", help="K splits of singular articles")

    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    parent = args.parent
    initial = args.initial
    K = int(args.K)
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
        eqcount, meqcount = next_eqid()
        #print(eqcount)
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
                        '''
                        sub_ids = []
                        for sub_eq in split_eqs:
                            sub_eq = remove_whitespace(sanitize_equation(sub_eq,complete=True))
                            if sub_eq not in unique_eqs:
                                if not initial:
                                    result = get_eqid(mask(beq+sub_eq+eeq))
                                    if result == '':
                                        eqid = "EQDS"+str(eqcount)+"Q"
                                        eqcount += 1
                                    else:
                                        eqid = result
                                else:
                                    eqid = "EQDS"+str(eqcount)+"Q"
                                    eqcount += 1
                                unique_eqs[sub_eq] = (eqid,mask(beq+sub_eq+eeq),1)
                            else: # increment freq count
                                prev = unique_eqs[sub_eq]
                                unique_eqs[sub_eq] = (prev[0], prev[1], prev[2]+1)
                            doc_list[sub_eq].add(document_name)
                            sub_ids.append(unique_eqs[sub_eq][0].rstrip('_F'))
                        '''
                        if equation not in unique_meqs:
                            if not initial:
                                result = get_eqid(mask(equation))
                                print(result)
                                if result == '':
                                    eqid = "EQDM"+str(meqcount)+"Q"
                                    meqcount += 1
                                else:
                                    eqid = result
                            else:
                                eqid = "EQDM"+str(meqcount)+"Q"
                                meqcount += 1
                            #unique_meqs[equation] = (eqid,",".join(sub_ids),equation, 1)
                            unique_meqs[equation] = (eqid, mask(equation), 1)
                        else:
                            prev = unique_meqs[equation]
                            unique_meqs[equation] = (prev[0], prev[1], prev[2]+1)
                        doc_list[equation].add(document_name)
                        break
                    else:
                        if flt_eq not in unique_eqs:
                            if not initial:
                                #print(flt_eq)
                                result = get_eqid(mask(beq+std_eq+eeq))
                                print(result)
                                if result == '':
                                    eqid = "EQDS"+str(eqcount)+"Q"
                                    eqcount += 1
                                else:
                                    eqid = result
                            else:
                                eqid = "EQDS"+str(eqcount)+"Q"
                                eqcount += 1
                            unique_eqs[flt_eq] = (eqid,mask(beq+std_eq+eeq), 1)
                        else:
                            prev = unique_eqs[flt_eq]
                            unique_eqs[flt_eq] = (prev[0], prev[1], prev[2]+1)
                        doc_list[flt_eq].add(document_name)
                        break
    '''
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
    '''
    print("{} single line equations".format(len(unique_eqs)))
    print("{} multiline equations".format(len(unique_meqs)))
    # print("{} seconds".format(int(time.time()-start)))
    pool.close()
    pool.join()

    """Merges two dictionaries"""
    eqs = {**unique_eqs, **unique_meqs}

    """Populates the database"""
    populate_db(eqs, doc_list)

    """Split into singular and nonsingular articles"""
    separate_articles(eqs, doc_list, './sep', K)

if __name__ == '__main__':
    main()

