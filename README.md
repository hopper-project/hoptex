# hoptex

There are three main scripts in this folder: getarxivdata.py, parsetex.py,and proctex.py.
Classes and their supporting JSON handler function are stored in core/texclasses.

## getarxivdata.py:
getarxivdata accepts a directory of .tex files, and in the parent directory of those .tex files, generates a metadata file of all of the files and their categories.

## parsetex.py
* Note: getarxivdata *must* be run on the folder of .tex files you're going to pass in.

parsetex.py accepts a directory of tex files. It begins by tokenizing each expression, finding LaTeX's markup tags (e.g. \\int), before generating total token counts by category for every file in the directory.

It then generates a folder of matplotlib bar graphs (stored in the parent directory of the .tex files). Each graph is sorted by the top 20 most frequently occurring tokens for that category.

## proctex.py

proctex.py accepts a dictionary of .tex files. It processes in each document, isolating display mode equations, and generating a nested data structure of document and equation objects.

These objects are stored into corresponding folders in the parent directory of the .tex files.
