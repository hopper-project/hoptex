import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
import time

def grab_eqs_and_filename(filename):
    return((filename,grab_math_from_file(filename)))

def main():
    parser = argparse.ArgumentParser(description='Usage for equation enumeration')
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    parser.add_argument("--xhtml", help="Path to directory of xhtml files")
    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    outpath = os.path.abspath(args.outfile)
    xhtml = False
    if(args.xhtml):
        xhtml = os.path.abspath(args.xhtml)
    matches = []
    print("Starting timer...")
    start = time.time()
    print("Seeking .tex files...")
    folderlist = next(os.walk(directory))[1]
    for subfolder in folderlist:
        print("Finding .tex files in {}".format(subfolder))
        current_dir = os.path.join(directory,subfolder)
        matches += gettexfiles(current_dir)
    # for root, directories, filenames in os.walk(directory):
    #     for filename in fnmatch.filter(filenames, '*.tex'):
    #         matches.append(os.path.join(root, filename))
    # matches = list(reversed(matches))
    print("{} files found".format(len(matches)))
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
    unique_eqs = {}
    eqcount = 0
    if(xhtml):
        math_equations = pool.imap(grab_eqs_and_filename,matches)
        for tup in math_equations:
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
                        unique_eqs[equation] = ("EQ" + str(eqcount) + "Q",xhtml_equations[i])
                    else:
                        unique_eqs[equation] = ("EQ" + str(eqcount) + "Q","")
                    eqcount+=1
        pool.close()
        pool.join()
        print("WRITING TO FILE")
        with open(outpath,mode='w') as fh:
            for x in unique_eqs:
                fh.write(unique_eqs[x][0]+'\t'+repr(x)[1:-1].replace("\t","\\t")+'\t'+repr(unique_eqs[x][1])[1:-1].replace("\t","\\t")+'\n')
        exit()
    else:
        math_equations = pool.imap(grab_math_from_file,matches)
        for doceqs in math_equations:
            for equation in doceqs:
                if equation not in unique_eqs:
                    unique_eqs[equation] = "EQ" + str(eqcount) + "Q"
                    eqcount+=1
    print("{} equations".format(len(unique_eqs)))
    # print("{} seconds".format(int(time.time()-start)))
    exit()
    pool.close()
    pool.join()
    print("Assigning IDs to unique equations...")
    unique_eqs = {}
    eqcount = 0
    while len(math_equations)>0:
        if math_equations[-1] in unique_eqs:
            math_equations.pop()
            continue
        unique_eqs[math_equations[-1]] = "EQ" + str(eqcount) + "Q"
        # iterate over -1th element and pop as you add to unique dictionary
        # avoids memory issues
        math_equations.pop()
        eqcount += 1
    # print("{} seconds".format(int(time.time()-start)))
    print("Found {} unique equations".format(len(unique_eqs)))
    print("Writing to file...")
    with open(outpath,mode='w') as fh:
        for x in unique_eqs:
            fh.write(unique_eqs[x]+'\t'+repr(x)[1:-1]+'\n')
    print("Finished writing equations to file")
    # print("{} seconds".format(int(time.time()-start)))


if __name__ == '__main__':
    main()
