"""Classes for JSON object generation"""
import subprocess
from subprocess import PIPE
import os
class equation:
    def __init__(self,eqtext,fname, pos, nexttext, prevtext, index,mathml,desig = 'latex'):
        self.text = eqtext
        self.type = desig
        self.itemtype = "equation"
        self.prevtext = prevtext
        self.nexttext = nexttext
        self.file = fname
        self.index=index
        self.pos = pos
        self.mathml = mathml

    def __str__(self):
        return self.text

    def __repr__(self):
        return self.text

    # def gentokens():
    #     self.prevsenttoks = word_tokenize(self.prevsent)
    #     self.nextsenttoks = word_tokenize(self.nextsent)

    def tojson(self):
        return self.__dict__

class document:
    def __init__(self, fname,textarray):
        self.name = fname
        self.array = textarray
        self.itemtype = "document"

    def get_equations(self):
        ret = []
        for item in self.array:
            if isinstance(item,equation):
                ret.append(item)
        return(ret)

    def tojson(self):
        return self.__dict__

class archive:
    def __init__(self,directory_name,dictionary):
        self.dir = directory_name
        self.docdict = dictionary
    def save(self):
        print(self.dir)
        outfilepath = self.dir + ".pkl"
        if os.path.isfile(outfilepath):
            outfile = open(outfilepath)
        else:
            outfile = open(outfilepath,'w+')
        pickle.dump(self,outfile)
        outfile.close()

def JSONHandler(Obj):
    if hasattr(Obj, 'tojson'):
        return Obj.tojson()
    else:
        raise TypeError('Object is not JSON serializable')
