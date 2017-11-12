# IMPORTANT: for compatibility with `python setup.py make [alias]`, ensure:
# 1. Every alias is preceded by @[+]make (eg: @make alias)
# 2. A maximum of one @make alias or command per line
#
# Sample makefile compatible with `python setup.py make`:
#```
#all:
#	@make test
#	@make install
#test:
#	nosetest
#install:
#	python setup.py install
#```


help:
	@python setup.py make

distclean:
	@+make coverclean
	@+make prebuildclean
	@+make clean
prebuildclean:
	@+python -c "import shutil; shutil.rmtree('build', True)"
	@+python -c "import shutil; shutil.rmtree('dist', True)"
	@+python -c "import shutil; shutil.rmtree('easytextract.egg-info', True)"
coverclean:
	@+python -c "import os; os.remove('.coverage') if os.path.exists('.coverage') else None"
clean:
	@+python -c "import os; import glob; [os.remove(i) for i in glob.glob('*.py[co]')]"
	@+python -c "import os; import glob; [os.remove(i) for i in glob.glob('easytextract/*.py[co]')]"
	@+python -c "import os; import glob; [os.remove(i) for i in glob.glob('easytextract/tests/*.py[co]')]"
	@+python -c "import os; import glob; [os.remove(i) for i in glob.glob('easytextract/examples/*.py[co]')]"

installdev:
	python setup.py develop --uninstall
	python setup.py develop

install:
	python setup.py install

build:
	@make prebuildclean
	python setup.py sdist --formats=gztar,zip bdist_wheel
	python setup.py bdist_wininst

pypimeta:
	python setup.py register

pypi:
	twine upload dist/*

buildupload:
	@make testsetup
	@make build
	@make pypimeta
	@make pypi

none:
	# used for unit testing
