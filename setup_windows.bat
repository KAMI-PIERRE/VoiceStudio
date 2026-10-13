@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\python.exe goto install

py -3.12 -m venv .venv >nul 2>&1
if not errorlevel 1 goto install
py -3.11 -m venv .venv >nul 2>&1
if not errorlevel 1 goto install
python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto setup_failed

:install
.venv\Scripts\python.exe -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)"
if errorlevel 1 goto missing_python
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto setup_failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto setup_failed
echo Setup complete. Run start_windows.bat and open http://127.0.0.1:7860
echo The voice library downloads once on first use.
pause
exit /b 0

:missing_python
echo Install Python 3.12 or 3.11 with the Python Launcher, then rerun setup.
echo An existing environment must use Python 3.11 through 3.13.
pause
exit /b 1

:setup_failed
echo Setup failed. Check your internet connection and the error above, then rerun.
pause
exit /b 1
