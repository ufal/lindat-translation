#!/usr/bin/env python3
#coding: utf-8

import sys
import io
import StringIO

import logging
logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)


from translate.storage.tmx import tmxfile

#with open("../file_samples/The-Oppidum-project.tmx", 'rb') as fin:
#with open("../file_samples/sample.tmx", 'rb') as fin:
#with open("../file_samples/sample.xliff", 'rb') as fin:
    # tmx_file = tmxfile(fin, 'en', 'cs')
    #tmx_file = tmxfile(fin)
    #for unit in tmx_file.unit_iter():
        # print(unit.getsource(), node.gettarget())
        # print(unit.getsource())



def file2segments(inputfile):
    # test type of inputfile -- open if filename, stringstream if string,
    # use directly if stream, otherwise error
    # inputstream = inputfile
    logging.debug( type(inputfile))
    logging.debug('inputfile is str: {}'.format(isinstance(inputfile, str)))
    logging.debug('inputfile is stream: {}'.format(isinstance(inputfile, io.IOBase)))
    
    if isinstance(inputfile, io.IOBase):
        inputstream = inputfile
    elif isinstance(inputfile, str):
        try:
            inputstream = open(inputfile, 'rb')
        except:
            inputstream = StringIO(inputfile)
    
    logging.debug( type(inputstream))
    logging.debug('inputstream is stream: {}'.format(isinstance(inputstream, io.IOBase)))

    # guess type of input -- try to load as tmx and as xliff, otherwise assume
    # text
    # and extract input segments
    # and  extract metadata if possible
    inputsegments = None
    inputtype = None
    srclang = None
    tgtlang = None
    if inputtype == None:
        try:
            document = tmxfile(inputstream)
            inputtype = 'TMX'
            inputsegments = [unit.getsource() for unit in document.getunits()]
        except:
            inputtype = None
    if inputtype == None:
        try:
            # XLIFF
            pass
        except:
            inputtype = None
    if inputtype == None:
        # fallback: anything can be parsed as plain text
        inputtype = 'TXT'
        inputsegments = inputstream.readlines()    

    return (inputsegments, inputtype, srclang, tgtlang)

def translations2file(translationsegments, inputfile, tgtlang='en'):
    # again, detect input type and file type (share code)
    pass

    # insert translations
    outputstring = translationsegments.join('\n')

    # tmxfile -> unit -> settarget(targettext, lang=tgtlang)

    # return file contents as string
    return outputstring


inputsegments, inputtype, srclang, tgtlang = file2segments("../file_samples/sample.txt")
print(inputtype, srclang, tgtlang)
print(inputsegments, sep="\n")


