import os
import glob
import sys
import multiprocessing as mp
import re

def eqerrors(filename):
    with open(filename) as fh:
        text = fh.read()
    equations = re.findall(r'\<math.*?\<\/math>',text)
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
    for x in sys.argv[1:]:
        if not os.path.isfile(x):
            print("Error: {} is not a valid file".format(x),file=sys.stderr)
            continue
        lines = []
        timed_out = []
        failed = []
        with open(x) as fh:
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
        outputdir = x[:-4] + '_converted/'
        outputtedfiles = glob.glob(os.path.join(outputdir,'*.xhtml'))
        pool = mp.Pool(processes=mp.cpu_count())
        coverage = pool.map(eqerrors,outputtedfiles)
        errors, total = zip(*coverage)
        erroreqs = sum(errors)
        totaleqs = sum(total)
        print("{}/{} equations encountered nonfatal errors".format(erroreqs,totaleqs))
        print("{}% total coverage".format((1-erroreqs/totaleqs)*100))


if __name__ == '__main__':
    main()
