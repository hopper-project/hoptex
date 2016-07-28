import os
import sys
import glob
import urllib
import re
import multiprocessing as mp
#directory containing .tex files
path = '1506/'

#getcat generates the URL that it uses to query the site
#site passes back an XML, the category of which is matched using regex
def getcat(fname):
    url = 'http://export.arxiv.org/api/query?search_query=all:' + fname[:-4] + '&start=0&max_results=1'
    data = urllib.urlopen(url).read()
    category = re.findall(r'<arxiv:primary_category xmlns:arxiv=\"http://arxiv.org/schemas/atom\" term=\"(.*?)\" scheme=\"http://arxiv.org/schemas/atom\"/>',data,re.DOTALL)
    return (category[0])

#writes to file as 'filename' 'category'
def iterwrite(infile):
    fname = os.path.basename(infile)
    cat = getcat(fname)
    outstr = fname + " " + cat + " " + "\n"
    print(outstr)
    return outstr


def main():
    path = '1506/'
    #accepts one argument - the directory in which the tex files are located
    #directory passed in should not include '/'
    #checks whether or not the file is a directory
    if(len(sys.argv)>1):
        path = str(sys.argv[1]+'/')
        if not os.path.isdir(path):
            print("Error: passed parameter is not a directory")
            sys.exit()
    print("Output will be in {}.txt".format(path[:-1]))
    metadata = path[:-1] + '.txt'
    #writes to a text file corresponding to the folder name
    out = open(outname,'w')
    #generate list of files in the directory with a .tex file extension
    filelist= glob.glob(os.path.join(path,'*.tex'))
    #initialize the same number of threads as cpu cores
    cpucount = mp.cpu_count()
    pool = mp.Pool(processes=cpucount)
    #append to list/map to list is thread safe
    #that's being done with pool
    output = pool.map(iterwrite,filelist)
    #append to list is thread-safe
    #write to file is not, so that's done serially
    #this is going to be read in as a dict in parsetex, so order doesn't matter
    #empties file, but only after having everything to write in
    out.truncate()
    #write to file
    for obj in output:
        out.write(obj)

if __name__ == '__main__':
    main()
