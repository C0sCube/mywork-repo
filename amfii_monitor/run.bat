@echo off
title PY_APP_RUNNER
SETLOCAL

echo ==============================
echo Starting Python Application
echo ==============================

REM Move to script directory
cd /d %~dp0

REM Activate virtual environment if present
IF EXIST venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo Virtual environment not found. Running system Python...
)

REM Run main program
python main.py

echo.
echo ==============================
echo Program finished execution
echo ==============================

pause
ENDLOCAL