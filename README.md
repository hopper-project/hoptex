# hoptex

This folder and its associated scripts can be used for the parsing and processing of a folder of .tex documents into a

There are three main scripts in this folder: getarxivdata.py, parsetex.py,and proctex.py.
Classes and their supporting JSON handler function are stored in core/texclasses.

### getarxivdata.py:
getarxivdata accepts a directory of .tex files, and in the parent directory of those .tex files, generates a metadata file of all of the files and their categories.

### parsetex.py
* Note: getarxivdata *must* be run on the folder of .tex files you're going to pass in.

parsetex.py accepts a directory of tex files. It begins by tokenizing each expression, finding LaTeX's markup tags (e.g. \\int), before generating total token counts by category for every file in the directory.

It then generates a folder of matplotlib bar graphs (stored in the parent directory of the .tex files). Each graph is sorted by the top 20 most frequently occurring tokens for that category.

### proctex.py

proctex.py accepts a directory of .tex files. It processes in each document, isolating display mode equations, and generating a nested data structure of document and equation objects.

Currently temporarily defunct (in light convertlatex.py). Future updates will enable a --cached option that will allow you to pass in pre-generated xhtml, and will attempt to generate math on its own (using latexmlmath) if it doesn't have a cached xhtml file to reference.

### convertlatex.py

convertlatex.py accepts a directory of .tex files, and generates a folder of xhtml files, each of which contains only the math packages. If the math for a file takes longer than 60 seconds to process (often the case of latexml becoming unresponsive and/or leaking memory), it aborts the attempt to generate an xhtml file for that document file and prints a corresponding note of failure to stderr.

Each xhtml file is generated using the *latexml* and *latexmlpost* commands.

convertlatex.py uses the multiprocessing library and, by default, will utilize as many cores as your system has.

###### Installation/usage

convertlatex.py relies on a local, cloned copy of the LaTeXML repository within the folder. After you've cloned the hoptex directory to your location of choice, cd inside hoptex directory and clone the LaTeXML directory (https://github.com/brucemiller/LaTeXML) into hoptex (so that you wind up with a filepath of hoptex/LaTeXML), as follows:

> `git clone https://github.com/hopper-project/hoptex.git`

> `cd hoptex`

> `git clone https://github.com/brucemiller/LaTeXML.git`

**Make sure you have LaTeXML's prerequisites installed** (http://dlmf.nist.gov/LaTeXML/get.html).

cd into the LaTeXML directory and make/test LaTeXML (continuing from above):

> `cd LaTeXML`

>`perl Makefile.PL`

>`make`

> `make test`

If all goes smoothly, convertlatex.py should now be able to convert.
