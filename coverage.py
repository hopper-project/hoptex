import os
import glob
import sys
import multiprocessing as mp
import re
from core.funcs import *
def eqerrors(filename):
    with open(filename) as fh:
        text = fh.read()
    equations = re.findall(r'(?s)\<table.*?\<\/table>',text)
    partialerror = 0
    for eq in equations:
        if "ltx_ERROR" in eq:
            partialerror += 1
    return (partialerror, len(equations))

def main():
    timeouterror = " MathML conversion failed - timeout"
    conversionerror = " Conversion failed"
    pperror = " MathML postprocessing failed - timeout"
    if len(sys.argv)==1:
        print("Error: must pass in a log or logs", file=sys.stderr)
        sys.exit()
    outputdir = sys.argv[3]
    path = sys.argv[2]
    log = sys.argv[1]
    lines = []
    timed_out = []
    failed = []
    with open(sys.argv[1]) as fh:
        lines = fh.readlines()
    for line in lines:
        ex = line.strip().split(':')
        if len(ex)==2:
            if ex[1]==timeouterror:
                timed_out.append(ex[0])
            elif ex[1]==conversionerror:
                failed.append(ex[0])
    print("Failed: {}".format(len(failed)))
    print("Timed out: {}".format(len(timed_out)))
    total_failures = len(failed)+len(timed_out)
    xhtmlfilelist = glob.glob(os.path.join(outputdir,'*.xhtml'))
    mathfilelist = getmathfiles(path)
    pool = mp.Pool(processes=mp.cpu_count())
    coverage = pool.map(eqerrors,xhtmlfilelist)
    errors, total = zip(*coverage)
    erroreqs = sum(errors)
    totaleqs = sum(total)
    print("{}% nonfatal error equation coverage".format(round((1-erroreqs/totaleqs)*100,2)))
    print("{}% document coverage".format(round((1-total_failures/len(mathfilelist))*100,2)))


if __name__ == '__main__':
    main()
