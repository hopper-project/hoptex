import itertools
import operator
from collections import Counter
import re
import sys
import multiprocessing as mp
import glob
import os

def proc(package):
    out = package.split(',')
    for i, x in enumerate(out):
        out[i] = x.strip()
    return out

def getpackages(fname):
    with open(fname,mode='r',encoding='latin-1') as fh:
        doctext = fh.read()
    out = re.findall(r'\\usepackage(?:\[.*?\])*\{(.*?)\}',doctext)
    out = map(proc,out)
    out = [item for sublist in out for item in sublist]
    return out

def main():
    global path
    global outpath
    global eqoutpath
    #default path to directory with tex files
    path = '1506/'
    is_file = 0
    #The program accepts a directory to be analyzed
    #The directory should have the LaTeX files (entered without the '/')
    if(len(sys.argv)>1):
        path = os.path.join(str(sys.argv[1]),'')
    else:
        print("ERROR: No destination folder given", file=sys.stderr)
        exit()
    if not os.path.isdir(path):
        print("Error: invalid directory passed in", file=sys.stderr)
        sys.exit()
    #per getarxivdatav2, the metadata for tex files in a folder
    #should be in a .txt file of the same name
    #read in data
    #remove general subcategories
    #initialize number of threads to the number of cpu cores
    pool = mp.Pool(processes=mp.cpu_count())
    print("Initialized {} threads".format(mp.cpu_count()))
    #error handling for missing metadata file
    #load in the list of files and their categories
    filelist= glob.glob(os.path.join(path,'*.tex'))
    filelist = pool.map(os.path.abspath,filelist)
    print("Read in file metadata.")
    #each line of the form 'filename.tex' 'category'
    #this changes it to just 'filename' and 'category'
    outlist = pool.map(getpackages,filelist)
    flatlist = [item for sublist in outlist for item in sublist]
    c = Counter(flatlist)
    toprint = c.most_common(50)
    for x in toprint:
        print(x)
    pool.close()
    pool.join()

if __name__ == '__main__':
  main()
