@echo off
REM Change to the virtual environment Scripts folder
cd /d "C:\PERSONAL DATA\2.POC\AGENTS\.venv\Scripts"

REM Activate the virtual environment
call activate.bat

REM Change to the project directory
cd /d "C:\PERSONAL DATA\2.POC\AGENTS"

REM Run the Python application
python app.py

pause