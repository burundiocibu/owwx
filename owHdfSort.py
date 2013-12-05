#!/usr/bin/env python

import time, datetime, numpy, tables
from sys import stdin

from optparse import OptionParser
parser = OptionParser()

parser.add_option("-d", "--debug", default=0, dest="debug", action="count",
                  help="Increase the debugLevel")

parser.add_option("-i", "--input", dest="input",
                  type="string", action="store",
                  default="ow.h5",
                  help="Input HDF file.")

parser.add_option("-p", "--purge", dest="purge",
                  action=count, default=0,
                  help="remove entries that might be duplicates")

(options, args) = parser.parse_args()

if len(args) and options.inputFile == None:
    options.inputFile = args[0]

if options.debug:
    print options

fh = tables.openFile(options.input, mode = "a") 

for tbl in fh.iterNodes("/"):
    print "Sorting", tbl
    time=tbl.col('time')
    val=tbl.col('val')
    ts=time.argsort()
    time=time.take(ts)
    val=val.take(ts)
    tbl.modifyColumns(names=('time', 'val'), columns=(time, val))

    if options.purge:
        print "Purging duplicates from", tbl
        print "code me"

fh.close()
