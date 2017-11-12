#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Auxiliary functions library for reports extractor and dicom anonymization
# Copyright (C) 2017 Larroque Stephen
# Licensed under MIT License.
#

from __future__ import absolute_import

import os
import re

try:
    from scandir import walk # use the faster scandir module if available (Python >= 3.5), see https://github.com/benhoyt/scandir
except ImportError as exc:
    from os import walk # else, default to os.walk()

try:
    # to convert unicode accentuated strings to ascii
    from .unidecode import unidecode
    _unidecode = unidecode
except ImportError as exc:
    # native alternative but may remove quotes and some characters (and be slower?)
    import unicodedata
    def _unidecode(s):
        return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
    print("Notice: for reliable ascii conversion, you should pip install unidecode. Falling back to native unicodedata lib.")

try:
    from .tqdm import tqdm
    _tqdm = tqdm
except ImportError as exc:
    def _tqdm(*args, **kwargs):
        if args:
            return args[0]
        return kwargs.get('iterable', None)

def fullpath(relpath):
    '''Relative path to absolute'''
    if (type(relpath) is object or hasattr(relpath, 'read')): # relpath is either an object or file-like, try to get its name
        relpath = relpath.name
    return os.path.abspath(os.path.expanduser(relpath))

def recwalk(inputpath, sorting=True, folders=False, topdown=True, filetype=None):
    '''Recursively walk through a folder. This provides a mean to flatten out the files restitution (necessary to show a progress bar). This is a generator.'''
    if filetype and isinstance(filetype, list):
        filetype = tuple(filetype)  # str.endswith() only accepts a tuple, not a list
    # If it's only a single file, return this single file
    if os.path.isfile(inputpath):
        abs_path = fullpath(inputpath)
        yield os.path.dirname(abs_path), os.path.basename(abs_path)
    # Else if it's a folder, walk recursively and return every files
    else:
        for dirpath, dirs, files in walk(inputpath, topdown=topdown):	
            if sorting:
                files.sort()
                dirs.sort()  # sort directories in-place for ordered recursive walking
            # return each file
            for filename in files:
                if not filetype or filename.endswith(filetype):
                    yield (dirpath, filename)  # return directory (full path) and filename
            # return each directory
            if folders:
                for folder in dirs:
                    yield (dirpath, folder)

def replace_buggy_accents(s, encoding=None):
    """Fix weird encodings that even ftfy cannot fix"""
    # todo enhance speed? or is it the new regex on name?
    dic_replace = {
        '\xc4\x82\xc2\xa8': 'e',
        'ĂŠ': 'e',
        'Ăť': 'u',
        'â': 'a',
        'Ă´': 'o',
        'Â°': '°',
        'â': "'",
        'ĂŞ': 'e',
        'ÂŤ': '«',
        'Âť': '»',
        'Ă': 'a',
        'AŠ': 'e',
        'AŞ': 'e',
        'A¨': 'e',
        'A¨': 'e',
        'Ă': 'E',
        'â˘': '*',
        'č': 'e',
        '’': '\'',
    }
    for pat, rep in dic_replace.items():
        if encoding:
            pat = pat.decode(encoding)
            rep = rep.decode(encoding)
        s = s.replace(pat, rep)
    return s
