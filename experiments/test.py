#!/usr/bin/env python3
#coding: utf-8

import sys
import io

import logging
logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)


from translate.storage.tmx import tmxfile

# TODO languages
# read language codes from TMX file
# write language codes to TMX file (settarget has a second argument lang='xx')

# TODO change api: input will be string, not stream !!!!!

def data2string(inputdata):
    # determine type of inputfile
    if isinstance(inputdata, io.IOBase):
        # stream: read in
        inputdata.seek(0)
        inputstring = inputstream.read()
    elif isinstance(inputdata, str):
        try:
            # filename: open and read
            with open(inputfile, 'r') as inputstream:
                inputstring = inputstream.read()
        except:
            # string: just use it
            inputstring = inputdata
    else:
        assert False, "Bad type of inputdata: {}, must be stream, filename, or string".format(type(inputdata))
    
    return inputstream

# determine input type, extract segments and metadata
def string2doc(inputstring):
    inputtype = None
    inputdoc = None
    
    # TMX?
    if inputtype == None:
        #inputstream.seek(0)
        try:
            inputdoc = tmxfile(inputstring.encode('utf8'))
            inputtype = 'TMX'
        except:
            logging.debug(sys.exc_info()[0])
            inputtype = None
            #raise
    
    # XLIFF?
    if inputtype == None:
        try:
            # XLIFF
            # TODO
            # inputtype = 'XLIFF'
            pass
        except:
            inputtype = None
    
    # TXT fallback (anything can be parsed as plain text)
    if inputtype == None:
        inputdoc = inputstream
        inputtype = 'TXT'

    return inputdoc, inputtype

def doc2segments(inputdoc, inputtype):
    inputsegments = []
    if inputtype == 'TMX':
        inputsegments = [unit.getsource() for unit in inputdoc.getunits()]
    elif inputtype == 'XLIFF':
        # TODO
        pass
    elif inputtype == 'TXT':
        inputsegments = [line.rstrip('\n\r') for line in inputdoc]
    else:
        assert False, 'Unsupported input type: {}'.format(inputtype)
    return inputsegments


def file2segments(inputfile):
    inputstream = file2stream(inputfile)
    inputdoc, inputtype = stream2doc(inputstream)
    inputsegments = doc2segments(inputdoc, inputtype)
    return inputsegments, inputtype

# TODO cannot read TMX from string, only from file
# TODO cannot write TMX to string, only to file -- could do a temp file, but
# better find the source code and implement a string variant

# insert translations
def docAddTrans(translationsegments, inputdoc, inputtype):
    outputstring = None
    if inputtype == 'TMX':
        assert len(translationsegments) == len(inputdoc.getunits())
        for unit, translation in zip(inputdoc.getunits(), translationsegments):
            unit.settarget(translation)
        #outputstream = io.StringIO()
        #inputdoc.serialize(outputstream)
        #inputdoc.savefile(outputstream)
        #outputstring = outputstream.getvalue()
        inputdoc.save()
        outputstring = str(inputdoc)
    elif inputtype == 'XLIFF':
        # TODO
        pass
    elif inputtype == 'TXT':
        outputstring = '\n'.join(translationsegments)
    else:
        assert False, 'Unsupported input type: {}'.format(inputtype)
    return outputstring

def translations2file(translationsegments, inputfile):
    inputstream = file2stream(inputfile)
    inputdoc, inputtype = stream2doc(inputstream)
    outputstring = docAddTrans(translationsegments, inputdoc, inputtype)
    return outputstring


inputfile = "../file_samples/sample.tmx"
#inputfile = "../file_samples/sample.txt"
#inputfile = """Slezte z toho lustru, Donalde, vidím vás!
#Kolik třešní, tolik višní.
#"""
inputfile = """<?xml version="1.0" encoding="utf-8"?>
<tmx version="1.4">
  <header creationtool="SDLXLiff2Tmx" creationtoolversion="1.0" o-tmf="SDLXliff2Tmx Generic 1.0 Format" datatype="xml" segtype="sentence" adminlang="en-US" srclang="en-US" creationdate="20190724T150512Z" creationid="TMServe\SDLXliff2Tmx" />
  <body>
    <tu creationdate="20190724T150512Z" creationid="TMServe\SDLXliff2Tmx">
      <tuv xml:lang="en-GB">
        <seg>The Oppidum project is headed by Jakub Zamrazil, a Czech entrepreneur with a successful</seg>
      </tuv>
      <tuv xml:lang="cs-CZ">
        <seg>The Oppidum project is headed by Jakub Zamrazil, a Czech entrepreneur with a successful</seg>
      </tuv>
    </tu>
    <tu creationdate="20190724T150512Z" creationid="TMServe\SDLXliff2Tmx">
      <tuv xml:lang="en-GB">
        <seg>track record in real estate development, sales and marketing.</seg>
      </tuv>
      <tuv xml:lang="cs-CZ">
        <seg>track record in real estate development, sales and marketing.</seg>
      </tuv>
    </tu>
  </body>
</tmx>
"""


inputsegments, inputtype = file2segments(inputfile)

print("INPUT")
print(inputtype)
print(inputsegments, sep="\n")

translations = ["The nucmleus of an atom is composed of nucleons.",
    "My hovercraft is full of eels."]

result = translations2file(translations, inputfile)

print("OUTPUT")
print(result)

