import argparse
import os
import multiprocessing as mp
import fnmatch
from core.funcs import *
from collections import Counter
import time


def main():
    global outpath
    parser = argparse.ArgumentParser(description='Usage for equation enumeration1')
    parser.add_argument("directory",help="Path to directory of .tex files")
    parser.add_argument("outfile",help="Path to output file")
    args = parser.parse_args()
    directory = os.path.join(os.path.abspath(args.directory),'')
    outpath = os.path.abspath(args.outfile)
    matches = []
    print("Starting timer...")
    start = time.time()
    print("Seeking .tex files...")
    for root, directories, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, '*.tex'):
            matches.append(os.path.join(root, filename))
    matches = list(reversed(matches))
    print("{} files found".format(len(matches)))
    print("{} seconds".format(int(time.time()-start)))
    pool = mp.Pool(processes=mp.cpu_count())
    print("Grabbing math from files...")
    math_equations = pool.map(grab_math_from_file,matches)
    math_equations = [item for sublist in math_equations for item in list(reversed(sublist))]
    print("{} equations".format(len(math_equations)))
    print("{} seconds".format(int(time.time()-start)))
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
        # pop from list and iterate over 0th element for memory reasons
        math_equations.pop()
        eqcount += 1
    print("{} seconds".format(int(time.time()-start)))
    print("Found {} unique equations".format(len(unique_eqs)))
    print("Writing to file...")
    with open(outpath,mode='w') as fh:
        for x in unique_eqs:
            fh.write(unique_eqs[x]+'\t'+x.replace("\n","\\n").replace("\"","\\\"").replace("\t","\\t")+'\n')
    print("Finished writing equations to file")
    print("{} seconds".format(int(time.time()-start)))


if __name__ == '__main__':
    main()
