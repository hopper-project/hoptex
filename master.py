import os
import sys
import subprocess


def main():
    if len(sys.argv)!=4:
        print("Usage: python3 master.py /path/to/dir/of/tex/dirs/ /path/to/xhtml/output/ /path/to/json/output/")
        exit()
    path = os.path.abspath(sys.argv[1])
    xhtmlpath = os.path.abspath(sys.argv[2])
    jsonpath = os.path.abspath(sys.argv[3])
    cdir = os.listdir(path)
    outfolders = []
    folders = []
    for x in cdir:
        if os.path.isdir(x) and x[0]!='.':
            outfolders.append(os.path.split(x)[1])

    xhtml = []
    json = []
    for x in outfolders:
        xhtml.append(os.path.join(xhtmlpath,x+'_converted/'))
        json.append(os.path.join(jsonpath,x+'_json/'))

    for i, x in enumerate(outfolders):
        # print(outfolders[i],xhtml[i],json[i])
        proc = subprocess.Popen(["python3","convertlatex.py",outfolders[i]+'/',xhtml[i]])
        proc.wait()
        proc = subprocess.Popen(["python3","proctex.py",outfolders[i]+'/',xhtml[i],json[i]])
        proc.wait()

if __name__ == '__main__':
    main()
