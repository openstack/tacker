#!/usr/bin/python

import getopt
import re
import sys
import tempfile


def printusage():
    print('sync_test_requirements.py -g <globalrequirements>'
          ' -t <testrequirements>'
          ' [-o <outputfile>]')


def main(argv):
    globareqfile = ''
    testreqfile = ''
    outputfile = ''
    check = False
    try:
       opts, args = getopt.getopt(
           argv,"hg:t:o:",
           ["globalrequirements=", "testrequirements=", "outputfile="])
    except getopt.GetoptError:
       printusage()
       sys.exit(2)

    for opt, arg in opts:
       if opt == '-h':
          printusage()
          sys.exit()
       elif opt in ("-g", "--globalrequirements"):
          globareqfile = arg
       elif opt in ("-o", "--outputfile"):
          outputfile = arg
       elif opt in ("-t", "--testrequirements"):
          testreqfile = arg
    if not outputfile:
        with tempfile.NamedTemporaryFile(delete=False) as tempf:
            outputfile = tempf.name
        check = True
    if not (globareqfile and testreqfile and (outputfile or check)):
        printusage()
        sys.exit(2)

    lines = []
    gmodules = {}
    changed = 0
    with open(testreqfile) as testfile:
        lines = testfile.readlines()
    with open(globareqfile) as globalfile:
        globallines = globalfile.readlines()
        for gline in globallines:
            gline = gline.rstrip('\n')
            gmodulename = re.split('[<>=]', gline)[0]
            moduleparts = gline.split("#")
            modulepart = moduleparts[0].rstrip(" ")
            modulelicense = ("" if len(moduleparts) <= 1 else
                moduleparts[1].strip(" "))
            gmodules[gmodulename] =(modulepart, modulelicense)
    with open(outputfile, 'w') as ofile:
        for line in lines:
           if line.startswith('#'):
               ofile.write(line)
               continue
           line = line.rstrip('\n')
           modulename = re.split('[<>=]', line)[0]
           moduleparts = line.split("#")
           modulepart = moduleparts[0].rstrip(" ")
           modulelicense = ("" if len(moduleparts) <= 1 else
               moduleparts[1].strip(" "))
           if (gmodules.get(modulename) and
               (modulepart, modulelicense) != gmodules.get(modulename)):
               changed = 1
               if gmodules.get(modulename)[1]:
                   ofile.write(" # ".join(gmodules.get(modulename)) + "\n")
               else:
                   ofile.write(gmodules.get(modulename)[0] + "\n")
           else:
               ofile.write(line + "\n")
    if changed:
        if check:
            print("%s is not synchronized with global requirements." %
                testreqfile)
        else:
            print(testreqfile + " is changed.\n")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])
