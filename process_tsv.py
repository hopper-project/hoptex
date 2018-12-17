"""
process_tsv
- input: 4 column tsv, tex files
- output: mml files, json files, xhtml files, 5 column tsv
"""

import sys # handling arguments passed to function
import glob #  file path handling
import os #checking files and writing to/from files
import re
import multiprocessing as mp
import subprocess
import argparse
import time
import datetime
import queue
from subprocess import PIPE
from core.funcs import *
from core.texclasses import *
import json
from functools import partial

# CONSTANTS
TIMEOUT = 1000

# Cache paths on Habanero
TEX_CACHE = '/rigel/home/dpj2108/cache/tex_cache'
XHTML_CACHE = '/rigel/home/dpj2108/cache/xhtml_cache'
MML_CACHE = '/rigel/home/dpj2108/cache/mml_cache'
JSON_CACHE = '/rigel/home/dpj2108/cache/json_cache'
TSV_CACHE = '/rigel/home/dpj2108/cache/tsv_cache'
# MML_TSV_CACHE = '/rigel/home/dpj2108/cache/mml_tsv_cache'

# Destination paths on arxivlab
XHTML_DEST = '/local/pipeline/dest/xhtml_dest'
MML_DEST = '/local/pipeline/dest/mml_dest'
JSON_DEST = '/local/pipeline/dest/json_dest'
MML_TSV_DEST = '/local/pipeline/dest/mml_tsv_dest'

# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"

# Writes sanitized document text to clean_file_name
def writesanitized(sanitized, clean_file_name, error_path):
    outfile = os.path.join(error_path, clean_file_name + '.tex')
    with open(outfile, 'w') as fh:
        fh.write(sanitized)

# Generate .xhtml from given .tex file
def generate_xhtml(filename, xhtml_path, error_path, timeout=TIMEOUT):
    clean_file_name = os.path.splitext(os.path.basename(filename))[0]
    outfname = os.path.join(xhtml_path, clean_file_name + '.xhtml')
    outrawname = os.path.join(xhtml_path, clean_file_name+'.txt')

    # Check if .xhtml already exists
    if os.path.isfile(outfname):
        print('{}.xhtml: Already generated'.format(filename))
        return '{}.xhtml: Already generated'.format(filename)

    with open(filename, mode='r', encoding='latin-1') as f1:
        text = f1.read()
    # text = generate_sanitized_document(text)
    if len(text) == 0:
        print('{}: Error - no body found'.format(filename))
        return '{}: Error - no body found'.format(filename)

    # Generate .xml
    try:
        proc = subprocess.Popen(['latexml', '-'], stderr=PIPE, stdout=PIPE,
        stdin=PIPE)
        stdout_xml, stderr_xml = proc.communicate(text.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print('{}: MathML conversion failed - timeout'.format(filename))
        writesanitized(text, clean_file_name, error_path)
        return '{}: MathML conversion failed - timeout'.format(filename)
    except Exception as e:
        # print(e) # ADDED FOR TEST
        print('{}: XML Conversion failed'.format(filename))
        writesanitized(text, clean_file_name, error_path)
        return '{}: XML Conversion failed'.format(filename)

    # Generate .xhtml
    try:
        proc = subprocess.Popen(['latexmlpost', '--format=xhtml', '-'],
        stderr=PIPE, stdout=PIPE, stdin=PIPE)
        stdout_xhtml, stderr_xhtml = proc.communicate(stdout_xml, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print('{}: MathML postprocessing failed - timeout'.format(filename))
        writesanitized(text, clean_file_name, error_path)
        return '{}: MathML postprocessing failed - timeout'.format(filename)
    if len(stdout_xhtml.strip())==0: # THIS IS WHERE CONVERSION ERROR OCCURS
        # print(stdout2.strip()) # ADDED FOR TEST
        print('{}: XHTML Conversion failed'.format(filename))
        writesanitized(text, clean_file_name, error_path)
        return '{}: XHTML Conversion failed'.format(filename)

    stdout_xhtml = stdout_xhtml.decode()
    stdout_xhtml = re.sub(r'(href\=\").*?(LaTeXML\.css)(\")',r'\1\2\3', stdout_xhtml)
    stdout_xhtml = re.sub(r'(href=\").*?(ltx-article\.css)(\")',r'\1\2\3', stdout_xhtml)

    generatetxt = True
    if(generatetxt):
        with open(outrawname,'w') as fh:
            try:
                fh.write(stdout_xml.decode())
                #fh.write(stdout.decode('latin-1'))
            except:
                pass
    with open(outfname,'w') as fh: # Write .xhtml file
        fh.write(stdout_xhtml)

    return '' # Return empty string if everything went through

def generate_mml(tex_path_list, xhtml_path, tsv_path, mml_path, json_path, mml_tsv_path, error_path):
    tsv_dict = {} # EQID --> LaTeX
    tex_dict = {} # MathML --> EQID
    mml_dict = {} # EQID --> MathML
    shouldAppend = False

    # Load EQID and LaTeX into dictionary
    print('Loading TSV...')
    with open(tsv_path, mode='r', encoding='utf-8') as fh:
        print('Creating dictionary of EQID and LaTeX...')
        line_count = 0
        for line in fh:
            line_count += 1
            line = line.strip()
            linesplit = line.split('\t')

            if len(linesplit) == 4:
                eqid, eqtext, freq, _ = linesplit
            elif len(linesplit) == 5:
                eqid, eqtext, mml, freq, _ = linesplit

            beqtext = unmask(eqtext)
            tsv_dict[eqid] = beqtext

    print('Creating dictionary of MathML and LaTeX...')
    for tex_path in tex_path_list:
        f1 = open(tex_path, mode='r', encoding='latin-1')
        text = f1.read()
        f1.close()
        clean_name = os.path.basename(os.path.splitext(tex_path)[0])
        tex_xhtml_path = os.path.join(xhtml_path, clean_name + '.xhtml')

        if not os.path.exists(tex_xhtml_path):
            print('{}: Missing converted file - {}'.format(tex_path, tex_xhtml_path))
            return '{}: Missing converted file - {}'.format(tex_path, tex_xhtml_path)

        with open(tex_xhtml_path, 'r') as fh:
            tex_xhtml = fh.read()

        xhtml_equations = re.findall(r'(?s)\<table.*?\<\/table\>', tex_xhtml)
        xhtml_body = grab_body(text)
        if not xhtml_body:
            print('{}: Missing XHTML body'.format(tex_path))
            return '{}: Missing XHTML body'.format(tex_path)
        tex_equations = grab_math(text)

        # Check if number of equations in tex and xhtml match
        if len(tex_equations) != len(xhtml_equations):
            if len(xhtml_equations) != 0:
                print('{}: LaTeX/XHTML equation count mismatch {} {}'.format(tex_path, len(tex_equations), len(xhtml_equations)))
                sanitized_file = os.path.join(error_path, clean_name + '.tex')
                sanitized_text = generate_sanitized_document(tex_path)
                print('Attempting to sanitize: {}'.format(tex_path))
                if len(sanitized_text.strip()) == 0:
                    print('{}: LaTeXML failure'.format(tex_path))
                    return('{}: LaTeXML failure'.format(tex_path))
                else:
                    with open(sanitized_file, 'w') as fh:
                        fh.write(generate_sanitized_document(tex_path))
            return '{}: LaTeX/XHTML equation count mismatch: LaTeX - {}, XHTML - {}'.format(tex_path, len(tex_equations), len(xhtml_equations))

        else:
            mml_queue = queue.Queue()
            for i, x in enumerate(xhtml_equations):
                tempvar = '\n'.join(re.findall(r'(?s)\<math.*?\<\/math\>', x))
                if len(tempvar) == 0:
                    print('{}-{}: No math in table'.format(tex_path, i))
                    xhtml_equations[i] = ''
                else:
                    xhtml_equations[i] = tempvar
                    eq_mml = x
                    mml_queue.put(eq_mml)

            split = grab_math(text, split=1)
            export_list = []
            for i, x in enumerate(tex_equations):
                try:
                    index = split.index(x)
                    eq_latex = standardize_equation(x)
                    eq_latex = beq + eq_latex + eeq
                    if not mml_queue.empty():
                        tex_dict[mml_queue.get()] = eq_latex
                except:
                    print('{}: Equation matching failed'.format(tex_path))
                    return '{}: Equation matching failed'.format(tex_path)

                next_text = ''
                prev_text = ''
                for i in range(len(tex_equations)):
                    if split[index-1] not in tex_equations:
                        prev_text = split[index-1]
                    if split[index+1] not in tex_equations:
                        next_text = split[index+1]
                location = xhtml_body.find(x)
                neweq = equation(eqtext=x, fname=os.path.basename(tex_path), pos=location, nexttext=next_text,
                                 prevtext=prev_text, index=index, mathml=xhtml_equations[i])
                export_list.append(neweq)
            outfname = os.path.join(json_path, clean_name + '.json')
            try:
                print('Creating JSON files...')
                with open(outfname, 'w') as fh:
                    json.dump(export_list, fh, default=JSONHandler)
                print('JSON files created')
            except:
                print('{}: Equation export to JSON failed'.format(outfname))

    # Generate mml_dict
    print('Attaching EQID to MathML...')
    for eqid, eqtext in tsv_dict.items():
        for mml, eqtext2 in tex_dict.items():
            if eqtext == eqtext2:
                mml_dict[eqid] = mml

    print('Writing MathML to TSV file...')
    output_file = mml_tsv_path # 5 column .tsv
    outfile = open(output_file, 'a+')
    line_count = 0

    with open(tsv_path, mode='r', encoding='utf-8') as fg:
        for line in fg:
            line = line.strip()
            linesplit = line.split('\t')
            if len(linesplit) == 4:
                eqid, eqtext, freq, _ = linesplit
            elif len(linesplit) == 5:
                eqid, eqtext, mml, freq, _ = linesplit
            if 'IX' in eqid:
                continue

            try:
                mml_rep = mml_dict[eqid]
            except KeyError:
                continue
            line_count += 1

            # Generate mml files
            '''
            mml_eq_file = open(os.path.join(mml_path, eqid.lower() + '.mml'), 'w')
            mml_eq_file.write(mml_rep)
            mml_eq_file.close()
            '''

            # Write mml to tsv file
            mml_rep = mask('\"' + mml_rep + '\"')
            outfile.write('\t'.join(linesplit[0:-2])
                          + '\t' + mml_rep
                          + '\t' + linesplit[-2]
                          + '\t' + linesplit[-1] + '\n')

            if line_count % 1000 == 0:
                print(line_count)

    outfile.close()
    print('Loaded {} equations'.format(line_count))
    return ''

def store_data(tex_file_path, xhtml_path, json_path):
    # tex_file_path = path of the .tex file processed
    # TODO: Need to make sure the destination directories are there on arxivlab
    # Create the necessary required directories if nonexistent

    clean_name = os.path.basename(os.path.splitext(tex_file_path)[0])
    xhtml = os.path.join(xhtml_path, clean_name + '.xhtml')
    json = os.path.join(json_path, clean_name + '.json')
    # mml_files = os.listdir(MML_CACHE)

    # Store data in arxivlab
    try:
        # subprocess.call('scp {} arxivlab:{}'.format(xhtml, xhtml_dest))
        # subprocess.call(['scp', '{}'.format(xhtml), 'arxivlab:{}'.format(XHTML_DEST)])
        # subprocess.call('scp {} arxivlab:{}'.format(json, json_dest))
        subprocess.call(['chmod', '770', '{}'.format(json)])
        subprocess.call(['scp', '{}'.format(json), 'arxivlab:{}'.format(JSON_DEST)])
        '''
        for mml_file in mml_files:
            # subprocess.call('scp {} arxivlab:{}'.format(os.path.join(mml_cache, mml_file), mml_dest))
            subprocess.call(['scp', '{}'.format(os.path.join(MML_CACHE, mml_file)), 'arxivlab:{}'.format(MML_DEST)])
        '''
    except OSError:
        print('Error: Failed to store data to arxivlab - {}'.format(tex_file_path))
        # sys.exit()

def clean_data(tex_file_path, xhtml_path, json_path):
    # tex_file_path = path of the .tex file processed

    clean_name = os.path.basename(os.path.splitext(tex_file_path)[0])
    xhtml = os.path.join(xhtml_path, clean_name + '.xhtml')
    json = os.path.join(json_path, clean_name + '.json')
    mml_files = os.listdir(MML_CACHE)

    # Remove cache data
    try:
        subprocess.call(['rm', '{}'.format(tex_file_path)])
        subprocess.call(['rm', '{}'.format(xhtml)])
        subprocess.call(['rm', '{}'.format(json)])
        for mml_file in mml_files:
            subprocess.call(['rm', '{}'.format(os.path.join(MML_CACHE, mml_file))])
    except OSError:
        print('Error: Failed to remove data on Habanero - {}'.format(tex_file_path))
        # sys.exit()

def main():
    # tsv_file = ''
    # mml_path = ''
    start_time = time.time()
    parser = argparse.ArgumentParser(description='Conversion of sanitized LaTeX documents to XHTML')
    parser.add_argument('tex_path', help='Path to input directory of .tex files')
    parser.add_argument('xhtml_path', help='Path to output directory for .xhtml files')
    parser.add_argument('tsv_path', help='Input 4 column .tsv file for mml generation')
    parser.add_argument('--H', help='Flag indicating script run on Habanero', default=False, action='store_true')
    parser.add_argument('--tex_list', help='List of .tex files to process (txt)', default=None)
    parser.add_argument('--mml_path', help='Path to output directory for .mml files', default=MML_CACHE)
    parser.add_argument('--json_path', help='Path to output directory for .json files', default=JSON_CACHE)
    parser.add_argument('--timeout', help='Specify custom timeout', default=TIMEOUT)
    args = parser.parse_args()

    origdir = os.getcwd()
    tex_path = os.path.abspath(args.tex_path) # Initially remote if --H, 밑에 path 이용하는 부분들 고쳐야 함
    xhtml_path = os.path.abspath(args.xhtml_path) # Local, originally xhtml_path
    tex_list = args.tex_list # Local
    tsv_path = os.path.abspath(args.tsv_path) # Local
    mml_path = os.path.abspath(args.mml_path) # Local
    mml_suffix = ('_' + tex_list) if tex_list else ''
    mml_tsv_path = os.path.abspath(os.path.join(origdir, '5_cols{}.tsv'.format(mml_suffix)))
    json_path = os.path.abspath(args.json_path)

    print('Timeout: {}s'.format(args.timeout))

    # If script being run on Habanero
    if args.H:
        # Assumption: SLURM_ARRAY_TASK_ID == file list name
        if not tex_list:
            print('Error: File list not provided for parallelization')
            sys.exit()

        # Ensure that necessary directories exist
        if not os.path.exists(TEX_CACHE): os.mkdir(TEX_CACHE)
        if not os.path.exists(XHTML_CACHE): os.mkdir(XHTML_CACHE)
        if not os.path.exists(MML_CACHE + mml_suffix): os.mkdir(MML_CACHE + mml_suffix)
        if not os.path.exists(JSON_CACHE): os.mkdir(JSON_CACHE)
        if not os.path.exists(TSV_CACHE): os.mkdir(TSV_CACHE)

        # Fetch .tex files to process from tex_list
        tex_files = None
        with open(tex_list, 'r') as tl:
            tex_files = tl.readlines()

        # Process each .tex file one by one
        for tex_file in tex_files:
            try:
                # Copy .tex from arxivlab
                tex_file_path = os.path.join(tex_path, tex_file.strip())
                print(tex_file_path)
                print(TEX_CACHE)
                subprocess.call(['scp', 'arxivlab:{}'.format(tex_file_path), '{}'.format(TEX_CACHE)])
            except OSError:
                print('Error: Failed to fetch data')
                sys.exit()

            if not os.path.exists(xhtml_path): os.mkdir(xhtml_path)
            os.chdir(xhtml_path)
            xhtml_error_path = os.path.join(os.path.split(os.path.normpath(xhtml_path))[0],
                                            os.path.basename(os.path.normpath(tex_path)) + '_failed')
            if not os.path.exists(xhtml_error_path): os.mkdir(xhtml_error_path)

            # Change value to local path
            tex_file_path = os.path.join(TEX_CACHE, tex_file.strip())

            print('Beginning processing of {}'.format(tex_file_path))

            print('Grabbing math from file...')
            result = hasmath(tex_file_path)
            if result[1] == 0:
                print('No math found')
                continue

            print('Generating XHTML...')
            message_xhtml = generate_xhtml(tex_file_path, xhtml_path, xhtml_error_path)

            print('Generating MathML representation...')
            message_mml = generate_mml([tex_file_path], xhtml_path, tsv_path, mml_path, json_path, mml_tsv_path, xhtml_error_path)

            with open(xhtml_path[:-1] + '.log', 'a+') as fh:
                if len(message_xhtml) > 0:
                    fh.write(message_xhtml + '\n')

            os.chdir(origdir)

            # Store data to arxivlab
            store_data(tex_file_path, xhtml_path, JSON_CACHE)

            # Clean up cache related to file
            clean_data(tex_file_path, xhtml_path, JSON_CACHE)

        # Store final eqs.tsv.mathml to arxivlab
        try:
            # subprocess.call('scp {} arxivlab:{}'.format(mml_tsv_path, mml_tsv_dest))
            subprocess.call(['scp', '{}'.format(mml_tsv_path), 'arxivlab:{}'.format(MML_TSV_DEST)])
            subprocess.call(['rm', mml_tsv_path])
        except OSError:
            print('Error: Failed to store 5 column tsv')
            # sys.exit()

    # Monthly/full directory processing
    else:
        if not os.path.exists(xhtml_path): os.mkdir(xhtml_path)
        os.chdir(xhtml_path)
        xhtml_error_path = os.path.join(os.path.split(os.path.normpath(xhtml_path))[0],
                                        os.path.basename(os.path.normpath(tex_path)) + '_failed')
        if not os.path.exists(xhtml_error_path): os.mkdir(xhtml_error_path)

        print("Beginning processing of {}".format(tex_path))
        print("Generating list of files with math...")
        filelist = getmathfiles(tex_path, tex_list)
        print("Generation complete.")
        pool = mp.Pool(processes=mp.cpu_count())
        print("Initialized {} threads".format(mp.cpu_count()))
        print("Beginning processing...")
        generate_xhtml_p = partial(generate_xhtml, xhtml_path=xhtml_path, error_path=xhtml_error_path)
        outlist = pool.map(generate_xhtml_p, filelist)
        # print(outlist)

        tsv = True
        if (tsv):
            print('Generating MathML representation...')
            generate_mml(filelist, xhtml_path, tsv_path, mml_path, json_path, xhtml_error_path)

        with open(xhtml_path[:-1] + ".log", 'w') as fh:
            for message in outlist:
                if len(message) > 0:
                    fh.write(message + '\n')
            end_time = time.time()
            total_time = str(datetime.timedelta(seconds=int(end_time - start_time)))
            fh.write("TIME (hh:mm:ss): {}\n".format(total_time))
        pool.close()
        pool.join()
        os.chdir(origdir)
        print("TIME: {}".format(total_time))

if __name__ == '__main__':
    main()
