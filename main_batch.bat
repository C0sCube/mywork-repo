@echo off
echo Activating virtual environment...
call C:\Users\Kaustubh.keny\Projects\office-work\mywork-repo\.venv\Scripts\activate.bat

echo Running the script...
python C:\Users\Kaustubh.keny\Projects\office-work\mywork-repo\main.py
echo Deactivating virtual environment...
call deactivate

echo Done.
pause
