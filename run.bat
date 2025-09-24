@echo off

REM Change to the directory where your project and virtual environment are located
cd C:\Users\rando\Office Projects\mywork-repo

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Run your Python script
python main.py

REM Optional: Deactivate the virtual environment after the script finishes
REM deactivate

REM Optional: Keep the command window open after execution for viewing output
pause