@echo off
REM Navigate to your Flask project directory
cd "C:\Users\kaustubh.keny\Projects\OFFICE PROJECTS\mywork-repo\web"

REM Activate the virtual environment
call "..\.venv\Scripts\activate.bat"

REM Run the Flask app
python web.py

REM Keep the command window open after execution
pause