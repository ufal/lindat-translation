#!/usr/bin/env python3
#coding: utf-8

import sys

import logging
logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO)


from translate.storage.tmx import tmxfile
with open("../file_samples/The-Oppidum-project.tmx", 'rb') as fin:
    tmx_file = tmxfile(fin, 'en', 'cs')
    for node in tmx_file.unit_iter():
        print(node.getsource(), node.gettarget())



def file2segments(inputfile):
    # test type of inputfile -- open if filename, stringstream if string,
    # use directly if stream, otherwise error
    inputstream = inputfile
    pass
    
    # guess type of input -- try to load as tmx and as xliff, otherwise assume
    # text
    inputtype = 'TXT'
    pass

    # extract input segments
    inputsegments = inputstream.readlines()    

    # extract metadata if possible
    srclang = None
    tgtlang = None

    # return inputsegments, inputtype, srclang, tgtlang
    return (inputsegments, inputtype, srclang, tgtlang)

translations2file(translationsegments, inputfile):
    # again, detect input type and file type (share code)
    pass

    # insert translations
    outputstring = translationsegments.join('\n')

    # return file contents as string
    return outputstring

