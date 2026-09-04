@echo off
:: Change directory to your Django project root folder
cd /d "C:\Users\kaustubh.keny\Projects\OFFICE PROJECTS\working_fsparse"

:: Activate the local virtual environment
call .venv\Scripts\activate.bat

:: Run the Django development server on your specific host and port
cd /d "C:\Users\kaustubh.keny\Projects\OFFICE PROJECTS\working_fsparse\rep_fsparse_django_dropin"
python manage.py runserver NCOG-LPT-TCH-32.Cogencis.com:5000

pause
