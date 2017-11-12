REM @pyinstaller easytextract.py
REM @pyinstaller --noconsole --onefile easytextract_pyinstaller.spec
pyinstaller --clean --onedir easytextract_pyinstaller.spec > pyinstaller-log.txt 2>&1 & type pyinstaller-log.txt
pyi-archive_viewer dist\easytextract.exe -r -b > pyinstaller-dependencies.txt
pause
