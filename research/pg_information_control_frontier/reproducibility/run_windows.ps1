$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe src\experiments.py
& .\.venv\Scripts\python.exe src\reporting.py
