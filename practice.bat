@echo off
REM Double-click to start the Navigara dashboard in practice mode.
cd /d "%~dp0"
if not exist .venv (
  echo First run: setting things up, takes a minute...
  py -3 -m venv .venv || python -m venv .venv || (echo Python is not installed. See SETUP.md. & pause & exit /b 1)
)
.venv\Scripts\python -m pip install -q -r requirements.txt
.venv\Scripts\python run.py --practice
pause
