easytextract
======================

|PyPI-Status| |PyPI-Versions| |LICENCE|

Easy to use text extractor, from PDF, DOC, DOCX and other documents, including if necessary using OCR (via Tesseract).

This library can extract text from any type supported by Textract.

This library only exists because of the awesome work of the Textract team and Tesseract.

|Screenshot|

It runs under Python 2.7 (it was not tested nor developped with compatibility with Python 3 in mind, although it might work with some slight changes).

INSTALL
-------

In general, please refer to Textract documentation to install the appropriate softwares needed to extract text from the filetypes you need.

The rest of this section will describe the details for a basic setup.

PYTHON (all platforms: Linux, MacOSX, Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To run Easytextract from Python, you need Python > 2.7 and to pip install textract.

Then install the following libraries to support the filetypes you want:

* For PDF, pip install PDFMiner. To get additional features and better PDF extraction, you can install pdftotext, part of poppler or Xpdf.
* For OCR, you need to install Tesseract >= 3.02 (but not 3.0 nor 4!) and pdftoppm.
* For DOCX, pip install python-docx2txt.
* For DOC, install antiword in the location on Windows: C:\antiword\antiword.exe , for Linux and Mac you will need to change the path inside the script.
* to support other types such as audio, see https://textract.readthedocs.io/en/stable/#currently-supporting

WINDOWS
~~~~~~~
By using the Windows binary (only for Windows 64-bits), PDF and DOCX are directly supported.

To enable OCR, and install tesseract >= v3.02 (not v4!) for your platform beforehand. You also need to install pdftoppm.exe.

For DOC support (not DOCX as it is already supported natively), you will also need antiword installed in C:\antiword\antiword.exe.

LICENSE
-------------
easytextract was initially made by Stephen Larroque <LRQ3000> for the Coma Science Group - GIGA Consciousness - CHU de Liege, Belgium. The application is licensed under MIT License.


.. |LICENCE| image:: https://img.shields.io/pypi/l/easytextract.svg
   :target: https://raw.githubusercontent.com/lrq3000/easytextract/master/LICENCE
.. |PyPI-Status| image:: https://img.shields.io/pypi/v/easytextract.svg
   :target: https://pypi.python.org/pypi/easytextract
.. |PyPI-Versions| image:: https://img.shields.io/pypi/pyversions/easytextract.svg
   :target: https://pypi.python.org/pypi/easytextract
.. |Screenshot| image:: https://raw.githubusercontent.com/lrq3000/easytextract/master/img/easytextract_gui.png
