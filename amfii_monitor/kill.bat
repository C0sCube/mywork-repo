@echo off
echo ==============================
echo Stopping Python Application
echo ==============================

taskkill /FI "WINDOWTITLE eq PY_APP_RUNNER*" /T /F

echo Done.
pause