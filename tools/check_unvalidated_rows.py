import csv
from pathlib import Path
p = Path(r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\import_fallbacks_plan.csv")
if not p.exists():
    print('CSV_NOT_FOUND')
    raise SystemExit(1)
with p.open(newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    missing = []
    for i,row in enumerate(r, start=2):
        val = (row.get('validated') or '').strip()
        if not val.lower().startswith('yes'):
            missing.append((i, row.get('file_path','<unknown>'), val))
if not missing:
    print('ALL_ROWS_VALIDATED')
else:
    for ln,path,val in missing:
        print(f"line {ln}: {path} -> validated='{val}'")
