import subprocess
from subprocess import PIPE
from nltk.tokenize import word_tokenize
import os
class equation:
    def __init__(self,eqtext,fname, desig = 'latex'):
        self.text = eqtext
        self.type = desig
        self.itemtype = "equation"
        # self.prevtext = ""
        # self.nexttext = ""
        # self.prevtexttoks = []
        # self.nexttexttoks = []
        self.file = fname
        self.mathml = ""

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
        # arraylen = len(self.array)
        # for i in range(1,arraylen-1):
        #     if isinstance(self.array[i],equation):
        #         print("Found an equation :D")
        #         for x in range(i-1,-1,-1):
        #             if isinstance(self.array[x],str):
        #                 self.array[i].prevtext = self.array[x]
        #                 break
        #         for x in range(i+1,arraylen,1):
        #             if isinstance(self.array[x],str):
        #                 self.array[i].nexttext = self.array[x]
        #                 break
        # self.array = self.get_equations()

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
