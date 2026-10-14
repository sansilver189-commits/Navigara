#!/bin/bash
# Double-click to start the Navigara dashboard.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First run: setting things up (takes a minute)..."
  python3 -m venv .venv || { echo "Python 3 is not installed. See SETUP.md."; read -n1; exit 1; }
fi
.venv/bin/python -m pip install -q -r requirements.txt
.venv/bin/python run.py 
