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

