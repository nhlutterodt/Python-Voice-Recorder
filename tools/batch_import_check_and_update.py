import csv
import re
import subprocess
import os
import sys
from pathlib import Path

CSV_PATH = Path(r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\import_fallbacks_plan.csv")
# PYTHONPATH: repo src then repo root
PYTHONPATH = r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src;C:\Users\Owner\Voice Recorder\Python-Voice-Recorder"

if not CSV_PATH.exists():
    print('CSV_NOT_FOUND')
    raise SystemExit(1)

rows = []
with CSV_PATH.open(newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    for r in reader:
        # pad short rows so indexing by header works
        if len(r) < len(header):
            r += [''] * (len(header) - len(r))
        rows.append(r)

# determine indices by header names to be robust
def idx(name: str) -> int:
    try:
        return header.index(name)
    except ValueError:
        raise SystemExit(f"Missing expected column in CSV header: {name}")

NEW_IMPORT_IDX = idx('new_import')
VALIDATED_IDX = idx('validated')
FILE_PATH_IDX = idx('file_path')

changed = False
for i, r in enumerate(rows):
    validated = (r[VALIDATED_IDX] or '').strip()
    if validated.lower().startswith('yes'):
        continue
    new_import_field = (r[NEW_IMPORT_IDX] or '')
    file_path_field = (r[FILE_PATH_IDX] or '')

    # extract module paths from 'from x.y import ...' occurrences
    modules = re.findall(r'from\s+([\w\.]+)\s+import', new_import_field)

    # fallback: derive module path from the file_path if no explicit new_import
    if not modules:
        m = re.search(r'Python - Voice Recorder[\\/](.+)\.py', file_path_field)
        if m:
            rel = m.group(1).strip()
            mod = 'voice_recorder.' + rel.replace('/', '.').replace('\\', '.')
            modules = [mod]

    if not modules:
        print(f"SKIP (no module found): {file_path_field}")
        continue

    # create a python snippet that imports each module and prints a marker
    imports_snippet = '\n'.join([f"import {mod}\nprint('IMPORTED:{mod}')" for mod in modules])

    cmd = [sys.executable, '-c', imports_snippet]
    env = os.environ.copy()
    env['PYTHONPATH'] = PYTHONPATH
    print(f"Running import-check for row {i+2}: modules={modules}")
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    except Exception as e:
        print(f"ERROR running import check for {modules}: {e}")
        continue

    if res.returncode == 0:
        out = res.stdout.strip()
        print(f"PASS: {modules} -> stdout:\n{out}")
        rows[i][VALIDATED_IDX] = "Yes: import-checked locally (rechecked 2025-10-12)"
        changed = True
    else:
        print(f"FAIL: {modules} -> rc={res.returncode}\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}")

# write back CSV if changed
if changed:
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print('CSV_UPDATED')
else:
    print('NO_CHANGES')
