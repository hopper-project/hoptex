import sys
import glob
import os
import re
import multiprocessing as mp
import subprocess
import argparse
import time
import datetime
import queue
from subprocess import PIPE
import paramiko
import getpass
from core.funcs import *
from core.texclasses import *
import json
from functools import partial

# CONSTANTS
TIMEOUT = 1000
KEY_PATH = '/rigel/home/{}/.ssh/id_rsa'

# Cache paths on Habanero
TEX_CACHE = '/rigel/home/{}/hoptex/cache/tex_cache'
XHTML_CACHE = '/rigel/home/{}/hoptex/cache/xhtml_cache'
MML_CACHE = '/rigel/home/{}/hoptex/cache/mml_cache'
JSON_CACHE = '/rigel/home/{}/hoptex/cache/json_cache'
#TSV_CACHE = '/rigel/home/{}/cache/tsv_cache'
# MML_TSV_CACHE = '/rigel/home/dpj2108/cache/mml_tsv_cache'

# Destination paths on arxivlab
XHTML_DEST = '/local/hoptex/dest/xhtml_dest'
MML_DEST = '/local/hoptex/dest/mml_dest'
JSON_DEST = '/local/hoptex/dest/json_dest'
MML_TSV_DEST = '/local/hoptex/dest/mml_tsv_dest'

# Delimiters for assembling
beq = "\\begin{equation}"
eeq = "\\end{equation}"

# TODO: Modify this function to take in an equation_tex instead of full text of .tex file
# Writes sanitized document text to clean_file_name
def writesanitized(sanitized, clean_file_name, error_path):
    outfile = os.path.join(error_path, clean_file_name + '.tex')
    with open(outfile, 'w') as fh:
        fh.write(sanitized)

# Generate .xhtml for given equation
def generate_xhtml(tex_file, eq_idx, equation_tex, xhtml_path, error_path, timeout=TIMEOUT):
    tex_eq_id = tex_file + '_{}'.format(eq_idx)
    outfname = os.path.join(xhtml_path, tex_eq_id + '.xhtml')
    outrawname = os.path.join(xhtml_path, tex_eq_id + '.txt')
    error_flag = False

    # Check if .xhtml already exists
    if os.path.isfile(outfname):
        error_flag = True
        print('{}.xhtml: Already generated'.format(tex_eq_id))
        return (error_flag, '{}.xhtml: Already generated'.format(tex_eq_id))

    # Generate .xml
    try:
        proc = subprocess.Popen(['latexml', '-'], stderr=PIPE, stdout=PIPE,
                                    stdin=PIPE)
        stdout_xml, stderr_xml = proc.communicate(equation_tex.encode(), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        error_flag = True
        print('Timeout: MathML conversion failed - {}'.format(tex_eq_id))
        writesanitized(equation_tex, tex_eq_id, error_path)
        return (error_flag, 'Timeout: MathML conversion failed - {}'.format(tex_eq_id))
    except Exception as e:
        error_flag = True
        print('Error: XML Conversion failed - {}'.format(tex_eq_id))
        writesanitized(equation_tex, tex_eq_id, error_path)
        return (error_flag, 'Error: XML Conversion failed - {}'.format(tex_eq_id))

    # Generate .xhtml
    try:
        proc = subprocess.Popen(['latexmlpost', '--format=xhtml', '-'],
                                    stderr=PIPE, stdout=PIPE, stdin=PIPE)
        stdout_xhtml, stderr_xhtml = proc.communicate(stdout_xml, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        error_flag = True
        print('Timeout: MathML postprocessing failed - {}'.format(tex_eq_id))
        writesanitized(equation_tex, tex_eq_id, error_path)
        return (error_flag, 'Timeout: MathML postprocessing failed - {}'.format(tex_eq_id))
    if len(stdout_xhtml.strip()) == 0:
        error_flag = True
        print('Error: XHTML Conversion failed - {}'.format(tex_eq_id))
        writesanitized(equation_tex, tex_eq_id, error_path)
        return (error_flag, 'Error: XHTML Conversion failed - {}'.format(tex_eq_id))

    stdout_xhtml = stdout_xhtml.decode()
    stdout_xhtml = re.sub(r'(href\=\").*?(LaTeXML\.css)(\")', r'\1\2\3', stdout_xhtml)
    stdout_xhtml = re.sub(r'(href=\").*?(ltx-article\.css)(\")', r'\1\2\3', stdout_xhtml)

    '''
    generatetxt = False
    if generatetxt:
        with open(outrawname, 'w') as fh:
            try:
                fh.write(stdout_xml.decode())
            except:
                pass
    with open(outfname, 'w') as fh:  # Write .xhtml file
        fh.write(stdout_xhtml)
    '''

    return (error_flag, stdout_xhtml)

# Fetches equation MathML from equation XHTML
def fetch_mml(tex_eq_id, eq_xhtml):
    print('Fetching equation MathML...')
    '''
    with open(eq_xhtml_path, 'r') as fh:
        eq_xhtml = fh.read()
    '''

    eq_mml = re.findall(r'(?s)\<table.*?\<\/table\>', eq_xhtml)

    if len(eq_mml) != 1:
        if len(eq_mml) == 0:
            print('Error: No equation MathML found from equation XHTML - {}'.format(tex_eq_id))
            return None
        else:
            print('Error: More than one equation MathML found from equation XHTML - {}'.format(tex_eq_id))
            return None

    return eq_mml[0]

# Stores the generated files into arxivlab
def store_data(tex_file_path, json_path, xhtml_path=None, mml_path=None):
    # tex_file_path = path of the .tex file processed
    # Need to make sure the destination directories are there on arxivlab
    # Create the necessary required directories if nonexistent

    clean_name = os.path.basename(os.path.splitext(tex_file_path)[0])
    if xhtml_path:
        xhtml_list = [os.path.join(xhtml_path, xhtml_name) for xhtml_name in os.listdir(xhtml_path)]
    if mml_path:
        mml_list = [os.path.join(mml_path, mml_name) for mml_name in os.listdir(mml_path)]
    json = os.path.join(json_path, clean_name + '.json')

    # Store data in arxivlab
    try:
        if xhtml_path:
            for xhtml in xhtml_list:
                subprocess.call(['chmod', '777', xhtml])
                subprocess.call(['scp', xhtml, 'arxivlab:{}'.format(XHTML_DEST)])
        if mml_path:
            for mml in mml_list:
                subprocess.call(['chmod', '777', mml])
                subprocess.call(['scp', mml, 'arxivlab:{}'.format(MML_DEST)])
        subprocess.call(['chmod', '777', json])
        subprocess.call(['scp', json, 'arxivlab:{}'.format(JSON_DEST)])
    except OSError:
        print('Error: Failed to store cached data to arxivlab - {}'.format(tex_file_path))

def clean_data(tex_file_path, xhtml_path, json_path, mml_path):
    # tex_file_path = path of the .tex file processed
    clean_name = os.path.basename(os.path.splitext(tex_file_path)[0])
    # xhtml_list = [os.path.join(xhtml_path, xhtml_name) for xhtml_name in os.listdir(xhtml_path)]
    # mml_list = [os.path.join(mml_path, mml_name) for mml_name in os.listdir(mml_path)]
    json = os.path.join(json_path, clean_name + '.json')

    # Remove cache data
    try:
        subprocess.call(['rm', tex_file_path])
        '''
        for xhtml in xhtml_list:
            subprocess.call(['rm', xhtml])
        for mml in mml_list:
            subprocess.call(['rm', mml])
        '''
        subprocess.call(['rm', json])
    except OSError:
        print('Error: Failed to remove cached data on Habanero - {}'.format(tex_file_path))
        # sys.exit()

def main():
    username = getpass.getuser()
    parser = argparse.ArgumentParser(description='Conversion of sanitized LaTeX documents to XHTML')
    parser.add_argument('tex_path', help='Path to input directory of .tex files')
    parser.add_argument('--initial', help='Flag indicating initial processing', default=False, action='store_true')
    parser.add_argument('--singular', help='Flag indicating singular article processing', default=False, action='store_true')
    parser.add_argument('--tex_list', help='List of .tex files to process (txt)', default=None)
    parser.add_argument('--xhtml_path', help='Path to output directory for .xhtml files', default=XHTML_CACHE.format(username))
    parser.add_argument('--mml_path', help='Path to output directory for .mml files', default=MML_CACHE.format(username))
    parser.add_argument('--json_path', help='Path to output directory for .json files', default=JSON_CACHE.format(username))
    parser.add_argument('--timeout', help='Specify custom timeout', default=TIMEOUT)
    args = parser.parse_args()

    origdir = os.getcwd()
    tex_list = args.tex_list
    arr_suffix = ('_' + tex_list) if tex_list else ''
    tex_path = os.path.abspath(args.tex_path)
    xhtml_path = os.path.abspath(args.xhtml_path + arr_suffix) # DEFAULT: XHTML_CACHE_${SLURM_ARRAY_TASK_ID}
    mml_path = os.path.abspath(args.mml_path + arr_suffix) # DEFAULT: MML_CACHE_${SLURM_ARRAY_TASK_ID}
    json_path = os.path.abspath(args.json_path) # DEFAULT: JSON_CACHE

    start_time = time.time()

    print('Timeout: {}s'.format(args.timeout))

    mode = 'initial' if args.initial else 'monthly'
    article_type = 'singular' if args.singular else 'nonsingular'
    print('Running {} {} article processing...'.format(mode, article_type))

    # Singular articles processing
    if args.singular and not tex_list:
        print('Error: File list not provided for parallelization')
        sys.exit()

    # Ensure that necessary directories exist
    if not os.path.exists(TEX_CACHE.format(username)): os.mkdir(TEX_CACHE.format(username))
    # if not os.path.exists(XHTML_CACHE.format(username) + arr_suffix): os.mkdir(XHTML_CACHE.format(username) + arr_suffix)
    # if not os.path.exists(MML_CACHE.format(username) + arr_suffix): os.mkdir(MML_CACHE.format(username) + arr_suffix)
    if not os.path.exists(JSON_CACHE.format(username)): os.mkdir(JSON_CACHE.format(username))

    if args.singular:
        # Fetch .tex files to process from tex_list
        try:
            with open(tex_list, 'r') as tl:
                tex_files = [tex_file.strip() for tex_file in tl.readlines()]
        except FileNotFoundError:
            print('Error: Provided article list does not exist')
            sys.exit()

    else:
        # Fetch .tex files to process from arxivlab:tex_path
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        key = paramiko.RSAKey.from_private_key_file(KEY_PATH.format(username))
        ssh_client.connect('arxivlab.cs.columbia.edu', username=username, password=key)
        stdin, stdout, stderr = ssh_client.exec_command('cd {}; ls'.format(tex_path))
        tex_files = [tex_file.strip() for tex_file in stdout.readlines()]

    error_list = []

    total = len(tex_files)
    processed = 0.

    # Process each .tex file one by one
    for tex_file in tex_files:
        try:
            # Copy .tex from arxivlab
            tex_file_path = os.path.join(tex_path, tex_file.strip())
            subprocess.call(['scp', 'arxivlab:{}'.format(tex_file_path), TEX_CACHE.format(username)])
        except OSError:
            print('Error: Failed to fetch data - {}'.format(tex_file_path))
            sys.exit()

        if not os.path.exists(xhtml_path): os.mkdir(xhtml_path)
        os.chdir(xhtml_path)
        xhtml_error_path = os.path.join(os.path.split(os.path.normpath(xhtml_path))[0],
                                        os.path.basename(os.path.normpath(tex_path)) + '_failed')
        if not os.path.exists(xhtml_error_path): os.mkdir(xhtml_error_path)

        # Find usepackage, begin & end document statements for .xhtml generation
        tex_file_path = os.path.join(TEX_CACHE.format(username), tex_file.strip()) # Change to local path
        print('Processing {}...'.format(tex_file_path))
        with open(tex_file_path, mode='r', encoding='latin-1') as tf:
            text = tf.read()

        if len(text) == 0:
            print('Error: No body found - {}'.format(tex_file_path))
            error_list.append('Error: No body found - {}'.format(tex_file_path))
            continue

        # Needed for .json file generation
        xhtml_body = grab_body(text)
        if not xhtml_body:
            print('Error: Missing XHTML body - {}'.format(tex_file_path))
            continue

        # Fetch all math equations from the article
        print('Grabbing math from file...')
        grab_result = grab_math_from_file(tex_file_path, split=False)
        grab_result_split = grab_math_from_file(tex_file_path, split=True)[1]
        tex_equations = grab_result[1]

        json_export_list = []

        for eq_idx, tex_equation in enumerate(tex_equations):
            tex_eq_id = tex_file + '_{}'.format(eq_idx)
            print('Processing equation {}...'.format(tex_eq_id))

            # Check singleline vs. multiline
            is_single = None
            std_eq = standardize_equation(tex_equation)
            for expr in cap_expr_list:
                match = re.match(expr, tex_equation)
                if match:
                    if expr in multiline_list: # multiline
                        is_single = False
                        if not (args.initial and args.singular):
                            # print(mask(beq + tex_equation + eeq))
                            result = get_mathml(mask(tex_equation))
                    else: # singleline
                        is_single = True
                        if not (args.initial and args.singular):
                            # print(mask(beq + std_eq + eeq))
                            result = get_mathml(mask(beq + std_eq + eeq))

            if is_single == None:
                print('Error: Failed to check singleline vs. multiline - {}'.format(tex_file_path))
                error_list.append('Error: Failed to check singleline vs. multiline - {}'.format(tex_file_path))
                continue

            # If MathML version exists (not initial)
            if not args.initial and result != '':
                print('MathML representation already exists - {}'.format(tex_file_path))
                continue

            print('Generating XHTML...')
            equation_tex = format_tex_equation(text, tex_equation)
            generate_xhtml_p = partial(generate_xhtml, xhtml_path=xhtml_path, error_path=xhtml_error_path)
            result_xhtml = generate_xhtml_p(tex_file, eq_idx, equation_tex)
            if result_xhtml[0]:
                error_list.append(result_xhtml[1])
                continue

            print('Fetching MathML representation...')
            #eq_xhtml_path = os.path.join(xhtml_path, tex_eq_id + '.xhtml')
            eq_mml = fetch_mml(tex_eq_id, result_xhtml[1])

            if not eq_mml:
                continue

            try:
                if is_single: put_mathml(mask(beq + std_eq + eeq), eq_mml)
                else: put_mathml(mask(tex_equation), eq_mml)
                print('MathML representation stored in database - {}'.format(tex_eq_id))
            except RuntimeError:
                print('Error: Failed to store MathML representation to database - {}'.format(tex_eq_id))

            # Add equation to .json export list
            split_index = grab_result_split.index(tex_equation)
            next_text = ''
            prev_text = ''

            if grab_result_split[split_index - 1] not in grab_result:
                prev_text = grab_result_split[split_index - 1]
            if grab_result_split[split_index + 1] not in grab_result:
                next_text = grab_result_split[split_index + 1]

            location = xhtml_body.find(tex_equation)
            neweq = equation(eqtext=tex_equation, fname=os.path.basename(tex_file_path), pos=location,
                             nexttext=next_text, prevtext=prev_text, index=split_index, mathml=eq_mml)
            json_export_list.append(neweq)

        # Generate .json file for article
        clean_name = os.path.basename(os.path.splitext(tex_file_path)[0])
        outfname = os.path.join(json_path, clean_name + '.json')
        try:
            print('Creating JSON file...')
            with open(outfname, 'w') as fh:
                json.dump(json_export_list, fh, default=JSONHandler)
            print('JSON file created - {}'.format(outfname))
        except:
            print('Error: Equation export to JSON failed - {}'.format(outfname))
            error_list.append('Error: Equation export to JSON failed - {}'.format(outfname))

        os.chdir(origdir)

        # Store data to arxivlab
        store_data(tex_file_path, json_path)

        # Clean up cache related to file
        clean_data(tex_file_path, xhtml_path, json_path, mml_path)

        processed += 1
        # print('Progress: %.2f\%' % (processed / total))

    with open(xhtml_path + ".log", 'w') as fh:
        for message in error_list:
            if len(message) > 0:
                fh.write(message + '\n')
        end_time = time.time()
        total_time = str(datetime.timedelta(seconds=int(end_time - start_time)))
        fh.write("Elapsed Time (hh:mm:ss): {}\n".format(total_time))

    fh.close()

    # TODO: Remove all job-specific cache directories

    print('Elapsed Time (hh:mm:ss): {}\n'.format(total_time))

if __name__ == '__main__':
    main()
