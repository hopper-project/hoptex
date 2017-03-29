"""
Module for the generation of an EQID/TEX/MATHML/DOCCOUNT TSV
"""

"""Categories are as follows:

itemtype
file
mathml
pos
nexttext
text
index
prevtext
type
"""

import argparse
import re
import os
import time
import sys
import multiprocessing as mp
import shutil
import json
from collections import Counter
from core.funcs import *

class eqn:
    def __init__(self,text,eqid):
        self.text = text
        self.mathml = ''
        self.documents = Counter()
        self.eqid = eqid

def counter_to_string(c):
    """"Accepts a counter object, returns a csv string of
    the form key1:count1,key2:count2,...,keyn:countn
    """
    str_list = []
    for item in c:
        str_list.append(item + ':' + str(c[item]))
    return ','.join(str_list)

def load_json(filepath):
    """Return the list of dictionary-style JSON objects
    For our intents and purposes, this should always be a list of
    one or more dictionaries. Future updates may wish to update to reduce
    memory usage.
    """
    with open(filepath) as fh:
        data = json.load(fh)
    return data

def main():
    global output_tsv
    parser = argparse.ArgumentParser(
    description="Generate EQID/LaTeX/MathML TSV"
    )
    parser.add_argument('disp_tsv',help='Path to display mode TSV')
    parser.add_argument('jsonfolder',
    help='Path to corresponding directory of TSVs')
    parser.add_argument('output_tsv',help='Path to output TSV')
    args = parser.parse_args()
    input_tsv = args.disp_tsv
    json_path = args.jsonfolder
    output_tsv = args.output_tsv
    filelist = []
    eq_dict = {}
    meq_dict = {}
    print("Loading TSV")
    with open(input_tsv,'r') as fh:
        for line in fh:
            linesplit = line.rstrip('\n').split('\t')
            if len(linesplit)==2:
                eqid = linesplit[0]
                text = unmask(linesplit[1].strip())
                flat_eq = flatten_equation(text)
                if flat_eq not in eq_dict:
                    eq_dict[flat_eq] = eqn(text,eqid)
            if len(linesplit)==3:
                eqid = linesplit[0]
                text = unmask(linesplit[2].strip())
                if text not in meq_dict:
                    meq_dict[text] = eqn(text,eqid)
    print("Loading complete")
    print("Finding JSON files...")
    for root, folders, files in os.walk(json_path):
        for filename in files:
            if filename.endswith('.json'):
                filelist.append(os.path.join(root,filename))
    print("Found {} JSON files".format(len(filelist)))
    pool = mp.Pool(processes=mp.cpu_count())
    for eqlist in pool.imap(load_json,filelist):
        for jsoneq in eqlist:
            eqtext = jsoneq['text']
            if is_multiline(eqtext):
                try:
                    eqnobj = meq_dict[eqtext]
                except:
                    print("{} - equation mismatch".format(jsoneq['file']))
                    continue
            else:
                try:
                    eqnobj = eq_dict[flatten_equation(eqtext)]
                except:
                    print("{} - equation mismatch".format(jsoneq['file']))
                    continue
            if not eqnobj.mathml:
                eqnobj.mathml = jsoneq['mathml']
            eqnobj.documents[jsoneq['file']] += 1
    pool.close()
    pool.join()
    print("Writing to file")
    with open(output_tsv,'w') as fh:
        for item in eq_dict:
            try:
                eqnobj = eq_dict[item]
            except:
                continue
            line = []
            line.append(eqnobj.eqid)
            line.append(mask(eqnobj.text))
            line.append(mask("\""+eqnobj.mathml+"\""))
            line.append(counter_to_string(eqnobj.documents))
            fh.write('\t'.join(line)+'\n')
        for item in meq_dict:
            try:
                eqnobj = eq_dict[item]
            except:
                continue
            line = []
            line.append(eqnobj.eqid)
            line.append(mask(eqnobj.text))
            line.append(mask("\""+eqnobj.mathml+"\""))
            line.append(counter_to_string(eqnobj.documents))
            fh.write('\t'.join(line)+'\n')
    print("Complete")

if sys.flags.interactive:
    pass
else:
    if __name__=='__main__':
        main()
