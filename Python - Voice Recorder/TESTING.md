Getting started with tests (Windows / PowerShell)
-----------------------------------------------

This project uses pytest. The repository contains a development virtual environment under `..\venv`.

1) Activate the venv (PowerShell):

```powershell
Set-Location "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder"
. .\venv\Scripts\Activate.ps1
```

2) Install dev dependencies (one-time):

```powershell
# from project root
python -m pip install -r "Python - Voice Recorder\requirements_dev.txt"
```

3) Run the quick unit tests:

```powershell
# Run only tests marked as unit
python -m pytest -q -m unit
```

4) Run import and smoke checks (fast):

```powershell
python -m pytest -q -k import
```

5) Run the full test suite (may be slow):

```powershell
python -m pytest -q
```

Notes
- If you don't want to install all dev deps, use `tests/run_unit_checks.py` as a minimal runner for a subset of checks (no pytest required).
- GUI tests may require `QT_QPA_PLATFORM=offscreen` in headless CI. The test suite already sets this where appropriate.