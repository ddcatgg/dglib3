# -*- coding: utf-8 -*-
import os
import _pickle as pickle


class SafeDumper(object):
    def __init__(self, filename):
        self.dumpfile = filename
        self.dumpfile_new = filename + '.1'

    def save(self, obj):
        fp = open(self.dumpfile_new, 'wb')
        pickle.dump(obj, fp, pickle.HIGHEST_PROTOCOL)
        fp.close()
        if os.path.isfile(self.dumpfile):
            os.remove(self.dumpfile)
        os.rename(self.dumpfile_new, self.dumpfile)

    def load(self):
        for dumpfile in (self.dumpfile, self.dumpfile_new):
            if os.path.isfile(dumpfile):
                fp = open(dumpfile, 'rb')
                obj = pickle.load(fp)
                fp.close()
                return obj
