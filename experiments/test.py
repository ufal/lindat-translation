#!/usr/bin/env python3
#coding: utf-8

import sys
import io
from lxml import etree 

import logging
logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)


from translate.storage.tmx import tmxfile

# TODO languages
# read language codes from TMX file
# write language codes to TMX file (settarget has a second argument lang='xx')

def data2string(inputdata):
    # determine type of inputdata
    if isinstance(inputdata, io.IOBase):
        # stream: read in
        inputdata.seek(0)
        inputstring = inputdata.read()
    elif isinstance(inputdata, str):
        try:
            # filename: open and read
            with open(inputdata, 'r') as inputstream:
                inputstring = inputstream.read()
        except:
            # string: just use it
            inputstring = inputdata
    else:
        assert False, "Bad type of inputdata: {}, must be stream, filename, or string".format(type(inputdata))
    
    return inputstring

# determine input type, extract segments and metadata
def string2doc(inputstring):
    inputtype = None
    inputdoc = None
    
    # TMX?
    if inputtype == None:
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
        inputdoc = inputstring.split('\n')
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


def file2segments(inputdata):
    inputstring = data2string(inputdata)
    inputdoc, inputtype = string2doc(inputstring)
    inputsegments = doc2segments(inputdoc, inputtype)
    return inputsegments, inputtype

# TODO cannot write TMX to string, only to file -- could do a temp file, but
# better find the source code and implement a string variant

# insert translations
def docAddTrans(translationsegments, inputdoc, inputtype):
    outputstring = None
    if inputtype == 'TMX':
        assert len(translationsegments) == len(inputdoc.getunits())
        for unit, translation in zip(inputdoc.getunits(), translationsegments):
            unit.settarget(translation)
        
        # serialization in the tmxfile class does not work,
        # have to use the internal lxml serialization
        outputstring = etree.tostring(inputdoc.document, xml_declaration=True, encoding='utf-8')
        outputstring = outputstring.decode('utf8')    
        
    elif inputtype == 'XLIFF':
        # TODO
        pass
    elif inputtype == 'TXT':
        outputstring = '\n'.join(translationsegments)
    else:
        assert False, 'Unsupported input type: {}'.format(inputtype)
    return outputstring

def translations2file(translationsegments, inputdata):
    inputstring = data2string(inputdata)
    inputdoc, inputtype = string2doc(inputstring)
    outputstring = docAddTrans(translationsegments, inputdoc, inputtype)
    return outputstring


#inputdata = "../file_samples/sample.txt"
inputdata = """<?xml version="1.0" encoding="utf-8"?>
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
</tmx>"""

#inputdata = """Slezte z toho lustru, Donalde, vidím vás!
#Kolik třešní, tolik višní.
#"""

inputdata = "../file_samples/sample.tmx"
#inputdata = "../file_samples/sample.txt"

inputsegments, inputtype = file2segments(inputdata)

#print("INPUT", inputtype, ":")
#print(inputsegments, sep="\n")

translations = ["The nucmleus of an atom is composed of nucleons.",
    "My hovercraft is full of eels."]

result = translations2file(translations, inputdata)

#print("")
#print("OUTPUT:")
#print("")

print(result)

