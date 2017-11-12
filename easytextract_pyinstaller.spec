# -*- mode: python -*-

# Canonical (batch) commands to launch the building on win64:
# pyinstaller --onedir easytextract_pyinstaller.spec > pyinstaller-log.txt 2>&1 & type pyinstaller-log.txt
# pyi-archive_viewer dist\easytextract.exe -r -b > pyinstaller-dependencies.txt

block_cipher = None

# Import specific libraries to make sure that necessary non .py files are included
# IMPORTANT: for this to work, you need to uninstall these libraries from your python install, to avoid compatibility errors (or the one in csg_fileutil_libs, the goal is to have only one version on your system). Particularly useful if you get the error "file does not exist in temp directory".
# Note that textract >= 1.6.1 is necessary for pyinstaller to build correctly (else you will get a background error "pdf type not supported")
import os, sys
cur_path = os.path.realpath('.')
sys.path.append(os.path.join(cur_path, 'easytextract', 'csg_fileutil_libs'))  # for gooey spec file, because it does not support relative paths (yet?)

import gooey
gooey_root = os.path.dirname(gooey.__file__)
gooey_languages = Tree(os.path.join(gooey_root, 'languages'), prefix = 'gooey/languages')
gooey_images = Tree(os.path.join(gooey_root, 'images'), prefix = 'gooey/images')

import textract
textract_all_parsers = list(os.walk(os.path.join(os.path.dirname(textract.__file__), 'parsers')))[0][2]
textract_all_parsers_imports = ['textract.parsers.' + os.path.splitext(parser)[0] for parser in textract_all_parsers]

additional_resources = [
                        ('easytextract/csg_fileutil_libs/langdetect/utils', 'csg_fileutil_libs/langdetect/utils'),  # for messages.properties file
                        ('easytextract/csg_fileutil_libs/langdetect/profiles', 'csg_fileutil_libs/langdetect/profiles'),
                        ]

# Main pyinstaller spec
a = Analysis([os.path.join('easytextract', 'easytextract.py')],
             pathex=[os.path.join(cur_path, 'easytextract')],
             binaries=[],
             datas=additional_resources,
             hiddenimports=[os.path.join(cur_path, 'easytextract', 'csg_fileutil_libs')] + textract_all_parsers_imports,  # hidden python files sublibraries that are necessary
             hookspath=[],
             runtime_hooks=[],
             excludes=['pandas', 'numpy', 'matplotlib', 'mpl-data', 'zmq', 'IPython', 'ipykernel', 'tcl', 'Tkinter', 'jupyter_client', 'ipywidgets', 'unittest', 'ipython', 'ipython_genutils', 'jupyter_core'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          gooey_languages, gooey_images,  # Support for non .py files, we add them in to collected files
          name='easytextract',
          debug=False,
          strip=False,
          upx=True,
          windowed=True,
          console=True )
