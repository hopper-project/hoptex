from lxml import etree
import re
import glob
import os
import multiprocessing as mp
from collections import Counter

def analyze(filename):
    with open(filename) as fh:
        text = fh.read()
    text = re.sub(r'm(?:ml)?\:math',"math",text)
    root = etree.XML(text.encode())
    equations = root.findall(".//math")
    outertaglist = []
    displaylist = []
    for x in equations:
        for key, value in x.attrib.items():
            displaylist.append("{} = {}".format(key, value))
        outertaglist.append(x.getparent().tag)
    return(len(equations),Counter(outertaglist), Counter(displaylist))

def main():
    path = '/media/jay/Data1/phrvd/all/'

    filelist = glob.glob(os.path.join(path,'*.xml'))
    pool = mp.Pool(mp.cpu_count())
    outlist = pool.map(analyze,filelist)
    toteqs = 0
    maxthings = Counter()
    totdisplay = Counter()
    for x in outlist:
        toteqs += x[0]
        maxthings += x[1]
        totdisplay += x[2]
    print("\n{} equations in the entire corpus".format(toteqs))
    maxmostcommon = maxthings.most_common(10)
    displaymostcommon = totdisplay.most_common(10)
    print("\n10 most common parent tags:")
    for i, x in enumerate(maxmostcommon):
        print("{}: \"{}\" - {} occurrences".format(i+1,x[0],x[1]))
    print("\n10 most common attributes in the <math> tag:")
    for i, x in enumerate(displaymostcommon):
        print("{}: \"{}\" - {} occurrences".format(i+1,x[0],x[1]))
    pool.close()
    pool.join()
if __name__=='__main__':
    main()
