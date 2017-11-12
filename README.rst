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

Please pip install textract and install tesseract v3 (not v4!) for your platform beforehand.

For DOC support (not DOCX as it is already supported natively), you will also need antiword installed in C:\antiword\antiword.exe (for Linux and Mac you will need to change the path inside the script.)

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
