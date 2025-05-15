@echo off
echo Activating virtual environment...
call C:\Users\rando\OneDrive\Documents\mywork-repo\envPDF\Scripts\activate.bat

echo Running the script...
python C:\Users\rando\OneDrive\Documents\mywork-repo\main.py

echo Deactivating virtual environment...
call deactivate

echo Done.
pause
