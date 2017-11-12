#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Easytextract
# An easy to use text extractor from any files supported by Textract, including PDF, DOC and DOCX
# By Stephen Larroque @ Coma Science Group, GIGA Research, University of Liege
# Creation date: 2017-01-29
# License: MIT
#
# INSTALL NOTE:
# You need to pip install textract and install tesseract >= v3.02 for your platform before launching this script.
# To extract from .doc (not needed for .docx), you also need to unzip antiword in C:\antiword\antiword.exe
# Tested on Python 2.7.12
#
# TODO:
# * find a way to make Gooey recognize that tolerant and ocr are by default checked, so we can change back --ocr_disable to --ocr which makes more sense, same for tolerant.
# * add count of skipped files (because of different filetypes for example)
# * bug with input containing accentuated characters, the files will not be added (probably a bug of argparse, not Gooey)
# * migrate to pyocr? https://medium.com/@winston.smith.spb/python-ocr-for-pdf-or-compare-textract-pytesseract-and-pyocr-acb19122f38c
#

from __future__ import print_function

from _version import __version__

__all__ = ['main']

import os, sys
cur_path = os.path.realpath('.')
sys.path.append(os.path.join(cur_path, 'csg_fileutil_libs'))  # for unidecode, because it does not support relative paths (yet? they need to use __import__(path, globals(), level=2))

import re
import six
import shutil
import textract
import traceback

from tempfile import mkdtemp, mkstemp
from textract.parsers.utils import ShellParser

from csg_fileutil_libs import argparse
from csg_fileutil_libs import langdetect
from csg_fileutil_libs.pdfminer_pdf2txt import pdf2txt
from csg_fileutil_libs.tee import Tee

from csg_fileutil_libs.aux_funcs import replace_buggy_accents, _unidecode, _tqdm, recwalk

# For OCR image preprocessing, disabled for the moment because it reduces the accuracy (particularly for the disposition of multi-column documents)
#import PIL
#import PIL.Image
#import PIL.ImageFilter


##### Files auxiliary functions #####

def is_file(dirname):
    """Checks if a path is an actual file that exists"""
    if not os.path.isfile(dirname):
        msg = "{0} is not an existing file".format(dirname)
        raise ArgumentTypeError(msg)
    else:
        return dirname

def is_dir(dirname):
    """Checks if a path is an actual directory that exists"""
    if not os.path.isdir(dirname):
        msg = "{0} is not a directory".format(dirname)
        raise ArgumentTypeError(msg)
    else:
        return dirname

def is_dir_or_file(dirname):
    """Checks if a path is an actual directory that exists or a file"""
    if not os.path.isdir(dirname) and not os.path.isfile(dirname):
        msg = "{0} is not a directory nor a file".format(dirname)
        raise ArgumentTypeError(msg)
    else:
        return dirname

def get_fullpath(relpath):
    """Relative path to absolute"""
    if (type(relpath) is object or hasattr(relpath, 'read')): # relpath is either an object or file-like, try to get its name
        relpath = relpath.name
    return os.path.abspath(os.path.expanduser(relpath))


##### Custom extraction classes for textract #####

class MyDocParser(ShellParser):
    """Extract text from doc files using antiword (need to be placed in C:\antiword\antiword.exe or ~/antiword/antiword)."""

    def extract(self, filename, procpath=None, **kwargs):
        if procpath is None:
            if os.name == 'nt':
                procpath = 'C:/antiword/antiword.exe'
            else:
                procpath = '~/antiword/antiword'
        stdout, stderr = self.run([procpath, filename])
        return stdout

class MyPdfMinerParser(ShellParser):
    """Extract text from pdf files using the native python PdfMiner library"""

    def extract(self, filename, **kwargs):
        """Extract text from pdfs using pdfminer and pdf2txt.py wrapper."""
        # Create a temporary output file
        tempfilefh, tempfilepath = mkstemp(suffix='.txt')  # tesseract < 3.03 do not support "stdout" argument, so need to save into a file
        os.close(tempfilefh)  # close to allow writing to tesseract
        # Extract text from pdf using the entry script pdf2txt (part of PdfMiner)
        pdf2txt.main(['', '-o', tempfilepath, filename])
        #stdout, _ = self.run(['pdf2txt.py', filename])
        # Read the results of extraction
        with open(tempfilepath, 'rb') as f:
            res = f.read()
        # Remove temporary output file
        os.remove(tempfilepath)
        return res

class MyOCRParser(ShellParser):
    """Extract text from various image file formats or pdf containing scan images using tesseract-ocr (compatible with tesseract v3.02.02, only version currently available on Windows)"""
    
    def extract(self, filename, **kwargs):
        if filename.endswith('.pdf'):
            return self.extract_pdf(filename, **kwargs)
        else:
            return self.extract_image(filename, **kwargs)

    def preprocess_image(self, filename):
        # Preprocess image to enhance text extraction
        img = PIL.Image.open(filename)
        img = img.filter(PIL.ImageFilter.UnsharpMask(radius=6.8, percent=300, threshold=0))  # sharpen
        img = img.convert('L')  # convert to monochrome black and white
        # compute average intensity value
        #width,height = img.size
        #total = 0
        #for i in range(0,width):
        #    for j in range(0,height):
        #        total += img.getpixel((i,j))
        #mean = total / (width * height)
        # resize
        img = img.resize((img.size[0]*4, img.size[1]*4), PIL.Image.ANTIALIAS)  # resize to artificially increase DPI
        img = img.filter(PIL.ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))  # sharpen again
        # threshold!
        img = img.point(lambda x: 0 if x<128 else 255, '1') # could also use (255-mean) as threshold but it thresholds too much, it cancels the unsharp (bolding the characters)
        img.save(filename)  # overwrite image

    def extract_image(self, filename, **kwargs):
        """Extract text from various image file formats using tesseract-ocr (compatible with tesseract v3.02.02, only version currently available on Windows)"""
        # TODO: if proportion of image wrong, resize automatically to fit A4 proportions using PILLOW! if width > percentage_threshold, downsize width, else if width <, then downsize height.
        filename = os.path.abspath(filename)  # tesseract need absolute paths!
        dirpath = os.path.dirname(filename)
        # Preprocess image - DISABLED as this lowers the accuracy for some aspects (in particular it lowers the accuracy at detecting multiple columns and thus at separating text contents!)
        #self.preprocess_image(filename)
        # Create a temporary output txt file for tesseract
        tempfilefh, tempfilepath = mkstemp(suffix='.txt')  # tesseract < 3.03 do not support "stdout" argument, so need to save into a file
        os.close(tempfilefh)  # close to allow writing to tesseract
        tempfile = tempfilepath[:-4]  # remove suffix to supply as argument to tesseract, because tesseract always append '.txt'
        # if language given as argument, specify language for tesseract to use
        if 'language' in kwargs:
            args = ['tesseract', filename, tempfile, '-l', kwargs['language']]
        else:
            args = ['tesseract', filename, tempfile]

        stdout, _ = self.run(args)
        # Read the results of extraction
        with open(tempfilepath, 'rb') as f:
            res = f.read()
        # Remove temporary output file
        os.remove(tempfilepath)
        return res

    def extract_pdf(self, filename, **kwargs):
        """Extract text from pdfs using tesseract (per-page OCR) by converting each pdf page to an image."""
        temp_dir = mkdtemp()
        base = os.path.join(temp_dir, 'conv')
        contents = []
        try:
            if filename.endswith('.pdf'):
                stdout, _ = self.run(['pdftoppm', filename, base])  # from poppler or Xpdf, http://poppler.freedesktop.org

            for page in sorted(os.listdir(temp_dir)):
                page_path = os.path.join(temp_dir, page)
                page_content = self.extract_image(page_path, **kwargs)
                contents.append(page_content)
            return six.b('').join(contents)
        finally:
            shutil.rmtree(temp_dir)


##### Text extraction functions #####

def extract_text(doc_path, ocr=False, tolerant=False, filter_lang=['fr', 'en', 'nl'], accent_remove=False, ocr_force=False, verbose=False):
    """Extract text content from a PDF or DOC/DOCX file"""
    doc_text = None
    # List of accepted languages (to exclude gibberish pdf)
    langs_ok = filter_lang
    langs_ok_prob = 0.9  # probability of confidence necessary to not reject the lang
    # Extract text from document using parsers (and not OCR) and remove accentuated characters and strip blank spaces
    if not ocr_force:
        if doc_path.endswith('.doc'):  # .doc filetype needs antiword (not docx, use textract directly!)
            docparser = MyDocParser()
            doc_text = docparser.process(doc_path, 'utf8')
        else:  # other filetypes should be supported as-is
            try:
                if verbose:
                    print('Trying to decode with Textract default decoder for the filetype...')
                doc_text = textract.process(doc_path)
            except Exception as exc:
                if verbose:
                    print('Encountered the following error while trying to read the PDF file:')
                    print(str(exc))
                    print('Please check if you installed the required libraries for the target filetype (please check Textract documentation)')
                try:
                    if doc_path.endswith('pdf'):
                        if verbose:
                            print('Trying to decode with Textract native PDF decoder pdfminer, please wait...')
                        pdfminerparser = MyPdfMinerParser()
                        doc_text = pdfminerparser.process(doc_path, 'utf8')
                    else:
                        doc_text = None
                except Exception as exc:
                    if not tolerant:
                        raise
                    if verbose:
                        print('Encountered the following error while trying to read the document:')
                        print(str(exc))
                    doc_text = None
    # Clean up doc_text and check that it is not empty nor gibberish (eg, encoded PDF)
    try:
        if ocr_force:
            # If we want OCR, we raise directly an exception now
            raise Exception()
        if accent_remove:
            doc_text = _unidecode(replace_buggy_accents(doc_text.decode('utf8'), 'utf8')).lower().strip()
        else:
            doc_text = replace_buggy_accents(doc_text.decode('utf8'), 'utf8').lower().strip()
        # Failed to decode anything from document (maybe pdf contains only image and no text? Can try to use tesseract with textract but lot of work for not much...)
        if not doc_text:
            raise ValueError('No text extractable from the specified file.')
        elif filter_lang is not None:
            # Additional check by language
            lang_check = langdetect.detect_langs(doc_text)[0]
            if lang_check.lang not in langs_ok or lang_check.prob < langs_ok_prob:
                raise ValueError('No text extractable or language unrecognized from the specified file.')
    except Exception as exc:
        if not tolerant:
            raise
        if verbose:
            print('Encountered the following error while trying to read the PDF file:')
            print(str(exc))
        # Try to decode using OCR
        if ocr or ocr_force:
            if verbose:
                print('Will now try to decode the document via OCR. Please be patient, it takes a while...')
            ocrparser = MyOCRParser()
            doc_text = ocrparser.process(doc_path, 'utf8')
            if accent_remove:
                #doc_text = _unidecode(replace_buggy_accents(textract.process(doc_path, method='tesseract', language='fra').decode('utf8'), 'utf8')).lower().strip()  # Should work, but does not on Windows because you need tesseract v3.03 with support for "stdout", which is currently unavailable on Windows...
                doc_text = _unidecode(replace_buggy_accents(doc_text.decode('utf8'), 'utf8')).lower().strip()
            else:
                doc_text = replace_buggy_accents(doc_text.decode('utf8'), 'utf8').lower().strip()
        if not ocr or not doc_text:  # Failed again, raise the exception!
            raise
    doc_text = re.sub('[ \t\f\v]+', ' ', doc_text)  # replace abusive spaces
    doc_text = re.sub('[\n\r]+', '\n', doc_text)  # replace abusive line breaks
    doc_text = re.sub('(\r?\s?\n\r?\s?)+', '\n', doc_text)  # replace abusive line breaks
    # Failed to decode anything from document, raise exception
    if not doc_text:
        raise ValueError('No text extractable from the specified file.')
    # Detect language
    #try:
        #lang = langdetect.detect(doc_text)
    #except Exception as exc:
        #lang = 'fr'

    return doc_text

def extract_text_recursive(doc_root_dir, filetype=None, ocr=False, tolerant=False, lang_filter=['fr', 'en', 'nl'], accent_remove=False, ocr_force=False, verbose=False):
    # doc_root_dir can either be a directory or a list of files
    results = {}
    errors = []
    total = 0

    if filetype and isinstance(filetype, list):
        filetype = tuple(filetype)  # str.endswith() only accepts a tuple, not a list

    if isinstance(doc_root_dir, str):  # we got a directory path, we need to walk it (recursively!)
        temp = recwalk(doc_root_dir, folders=False, filetype=filetype)
        doc_dict = []
        for doc_dir, doc_filename in temp:
            doc_dict.append(os.path.join(doc_dir, doc_filename))
            total += 1
        del temp
    else:  # we got a list of files
        doc_dict = doc_root_dir
        total = len(doc_dict)

    # Main loop
    for doc_path in _tqdm(doc_dict, total=total, leave=True, unit='files', file=sys.stdout):
        # check filetype
        if not doc_path.endswith(filetype):
            continue

        # Attempt text extraction
        doc_text = None
        if verbose:
            print('* Processing file: %s' % doc_path)
        # Try to extract the text
        try:
            doc_text = extract_text(doc_path, ocr=ocr, tolerant=tolerant, accent_remove=accent_remove, ocr_force=ocr_force, verbose=verbose)
        except Exception as exc:
            # Error
            if 'Syntax Warning: May not be a PDF file' in str(exc) or 'File is not a zip file' in str(exc) or 'No text extractable' in str(exc) or 'Unsupported image type' in str(exc):
                # If the file is not a document, we just skip without any error
                doc_text = None
                if verbose:
                    print(str(exc))
                pass
            else:
                if tolerant:
                    print('The following error happened while processing this file:')
                    print(str(exc))
                    pass
                else:
                    raise
        if doc_text is None:
            errors.append(doc_path)
            if verbose:
                print('* Warning: error reading file %s, might not contain any text or unrecognized format, skipping file.' % doc_path)
        else:
            doc_filename = os.path.basename(doc_path)
            results[doc_filename] = doc_text
    return (results, errors)


##### GUI AUX FUNCTIONS #####

# Try to import Gooey for GUI display, but manage exception so that we replace the Gooey decorator by a dummy function that will just return the main function as-is, thus keeping the compatibility with command-line usage
try:  # pragma: no cover
    import gooey
except ImportError as exc:
    # Define a dummy replacement function for Gooey to stay compatible with command-line usage
    class gooey(object):  # pragma: no cover
        def Gooey(func):
            return func
    # If --gui was specified, then there's a problem
    if len(sys.argv) > 1 and 'cmd' not in sys.argv:  # pragma: no cover
        print('ERROR: --gui specified but an error happened with lib/gooey, cannot load the GUI (however you can still use this script in commandline). Check that lib/gooey exists and that you have wxpython installed. Here is the error: ')
        raise(exc)

def conditional_decorator(flag, dec):  # pragma: no cover
    def decorate(fn):
        if flag:
            return dec(fn)
        else:
            return fn
    return decorate

def check_gui_arg():  # pragma: no cover
    """Check that the --gui argument was passed, and if true, we remove the --gui option and replace by --gui_launched so that Gooey does not loop infinitely"""
    if len(sys.argv) > 1 or '--cmd' in sys.argv:
        # DEPRECATED since Gooey automatically supply a --ignore-gooey argument when calling back the script for processing
        #sys.argv[1] = '--gui_launched' # CRITICAL: need to remove/replace the --gui argument, else it will stay in memory and when Gooey will call the script again, it will be stuck in an infinite loop calling back and forth between this script and Gooey. Thus, we need to remove this argument, but we also need to be aware that Gooey was called so that we can call gooey.GooeyParser() instead of argparse.ArgumentParser() (for better fields management like checkboxes for boolean arguments). To solve both issues, we replace the argument --gui by another internal argument --gui_launched.
        return False
    else:
        return True

def AutoGooey(fn):  # pragma: no cover
    """Automatically show a Gooey GUI if --gui is passed as the first argument, else it will just run the function as normal"""
    if check_gui_arg():
        return gooey.Gooey(fn)
    else:
        return fn


##### Main program #####

@AutoGooey
def main(argv=None, return_report=False):
    if argv is None: # if argv is empty, fetch from the commandline
        argv = sys.argv[1:]
    elif isinstance(argv, _str): # else if argv is supplied but it's a simple string, we need to parse it to a list of arguments before handing to argparse or any other argument parser
        argv = shlex.split(argv) # Parse string just like argv using shlex

    #==== COMMANDLINE PARSER ====

    #== Commandline description
    desc = '''Easytextract v%s
Description: Easy to use text extractor, from PDF, DOC, DOCX and other document types, including if necessary using OCR (via Tesseract).

Note: use --cmd to avoid launching the graphical interface and use as a commandline tool.
    ''' % __version__
    ep = ''' '''

    #== Commandline arguments
    #-- Constructing the parser
    # Use GooeyParser if we want the GUI because it will provide better widgets
    if (not '--cmd' in argv and not '--ignore-gooey' in argv and not '--help' in argv and not '-h' in argv):  # pragma: no cover
        # Initialize the Gooey parser
        main_parser = gooey.GooeyParser(add_help=True, description=desc, epilog=ep, formatter_class=argparse.RawTextHelpFormatter)
        # Define Gooey widget types explicitly (because type auto-detection doesn't work quite well)
        widget_dir = {"widget": "DirChooser"}
        widget_filesave = {"widget": "FileSaver"}
        widget_file = {"widget": "FileChooser"}
        widget_text = {"widget": "TextField"}
        widget_multifile = {"widget": "MultiFileChooser"}
    else: # Else in command-line usage, use the standard argparse
        # Delete the special argument to avoid unrecognized argument error in argparse
        if len(argv) > 0 and '--ignore-gooey' in argv: argv.remove('--ignore-gooey') # this argument is automatically fed by Gooey when the user clicks on Start
        if len(argv) > 0 and '--cmd' in argv: argv.remove('--cmd')
        # Initialize the normal argparse parser
        main_parser = argparse.ArgumentParser(add_help=True, description=desc, epilog=ep, formatter_class=argparse.RawTextHelpFormatter)
        # Define dummy dict to keep compatibile with command-line usage
        widget_dir = {}
        widget_filesave = {}
        widget_file = {}
        widget_text = {}
        widget_multifile = {}

    # Required arguments
    main_parser.add_argument('-i', '--input', metavar='/some/path or /some/file.pdf', type=str, nargs='+', required=True, # type=argparse.FileType('r') to open directly
                        help='Input files to analyze (pdf, docx, doc or any other supported by Textract).', **widget_multifile)
    main_parser.add_argument('-o', '--output', metavar='/some/path', type=str, required=True,
                        help='Output folder where to store the extracted text files.', **widget_dir)

    # Optional output/copy mode
    main_parser.add_argument('--filetypes', metavar='pdf;docx', type=str, required=False, default='pdf;docx;doc',
                        help='Filter by filetype (limited by Textract support). Eg, pdf;docx;doc', **widget_text)
    main_parser.add_argument('-a', '--accent_remove', action='store_true', required=False, default=False,
                        help='Replace accentuated characters by their non-accentuated counterpart (great for post-processing).')
    main_parser.add_argument('--ocr_disable', action='store_true', required=False, default=False,
                        help='Disable OCR, which is used if document is unreadable otherwise. OCR takes additional time (using Tesseract v3).')
    main_parser.add_argument('--ocr_force', action='store_true', required=False, default=False,
                        help='Force OCR usage for any document type. Needs Tesseract v3 to work.')
    main_parser.add_argument('--tolerant_disable', action='store_true', required=False, default=False,
                        help='Tolerance: print and skip errors, else raise an exception (for debugging).')
    main_parser.add_argument('--lang_filter', metavar='fr;en', type=str, required=False, default='en;fr;nl',
                        help='Filter by language, leave this empty to disable. This is another check for gibberish text after PDF decoding. Eg, fr;en', **widget_text)
    main_parser.add_argument('-l', '--log', metavar='/some/folder/filename.log', type=str, required=False,
                        help='Path to the log file. (Output will be piped to both the stdout and the log file)', **widget_filesave)
    main_parser.add_argument('-v', '--verbose', action='store_true', required=False, default=False,
                        help='Verbose mode (show more output).')
    main_parser.add_argument('--silent', action='store_true', required=False, default=False,
                        help='No console output (but if --log specified, the log will still be saved in the specified file).')

    #== Parsing the arguments
    args = main_parser.parse_args(argv) # Storing all arguments to args

    #-- Set variables from arguments
    allinputpaths = args.input
    inputpaths = [get_fullpath(path) for path in allinputpaths]
    outputpath = get_fullpath(args.output)
    accent_remove = args.accent_remove
    filetypes = args.filetypes
    ocr = not args.ocr_disable
    ocr_force = args.ocr_force
    tolerant = not args.tolerant_disable
    lang_filter = args.lang_filter
    verbose = args.verbose
    silent = args.silent

    # -- Sanity checks
    # Strip trailing slashes to ensure we correctly format paths afterward
    inputpaths = [inpath.rstrip('/\\') for inpath in inputpaths]
    outputpath = outputpath.rstrip('/\\')

    # Check existence
    for inpath in inputpaths:
        if not os.path.exists(inpath):
            raise NameError('Specified input path does not exist: %s.' % inpath)
    if not os.path.exists(outputpath) or not os.path.isdir(outputpath):
        raise NameError('Specified output path does not exist or is not a directory. Please check the specified path.')

    # Preprocess lang filter or disable (same for filetypes)
    if not lang_filter:  # empty lang filter, we disable
        lang_filter = None
    else:
        lang_filter = lang_filter.split(';')  # else make a list
    if not filetypes:  # empty filetypes, we disable
        filetypes = None
    else:
        filetypes = filetypes.split(';')  # else make a list

    # -- Configure the log file if enabled (ptee.write() will write to both stdout/console and to the log file)
    if args.log:
        ptee = Tee(args.log, 'a', nostdout=silent)
        #sys.stdout = Tee(args.log, 'a')
        sys.stderr = Tee(args.log, 'a', nostdout=silent)
    else:
        ptee = Tee(nostdout=silent)

    # -- Main routine
    print('== Easytextract ==')
    print('Extracting text contents, please wait...')
    all_texts, errors = extract_text_recursive(inputpaths, filetype=filetypes, ocr=ocr, tolerant=tolerant, lang_filter=lang_filter, accent_remove=accent_remove, ocr_force=ocr_force, verbose=verbose)
    print('Total documents successfully extracted: %i' % len(all_texts))

    # Display unreadable (error) reports
    if errors:
        print('Total number of unreadable documents: %i. Here is the detailed list:' % len(errors))
        for err in errors:
            print('* %s' % err)

    # Write the extracted text content(s) to text file(s)
    import codecs
    for filename, text in all_texts.items():
        outfilepath = os.path.join(outputpath, filename+'.txt')
        if accent_remove:
            with open(outfilepath, 'w') as f:  # does not support writing accentuated characters, but it writes as ascii, which is nice
                f.write(text)
        else:
            with codecs.open(outfilepath, mode='w', encoding='utf-8') as f:  # supports accentuated characters
                f.write(text)
    print('Saved extracted text contents to %s' % outputpath)

    return 0


# Calling main function if the script is directly called (not imported as a library in another program)
if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
