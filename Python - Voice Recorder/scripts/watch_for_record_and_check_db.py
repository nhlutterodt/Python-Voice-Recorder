#!/usr/bin/env python3
"""Watch recordings/raw for the next new .wav and run scripts/inspect_db.py when found.

Run this while the GUI is open; it will exit after detecting one new file and printing the DB inspection.
"""
import time
import subprocess
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
raw_dir = project_root / 'recordings' / 'raw'
raw_dir.mkdir(parents=True, exist_ok=True)

print('Watcher started, monitoring:', raw_dir)
existing = set(p.name for p in raw_dir.glob('*.wav'))
print(f'existing files: {len(existing)}')

timeout = 180  # seconds
deadline = time.time() + timeout
while time.time() < deadline:
    cur = set(p.name for p in raw_dir.glob('*.wav'))
    new = cur - existing
    if new:
        found = sorted(list(new))[-1]
        found_path = raw_dir / found
        print('Detected new recording:', found_path)

        # Run the DB inspector using the same Python executable that's running this watcher
        inspect_script = project_root / 'scripts' / 'inspect_db.py'
        try:
            print('Running DB inspector...')
            res = subprocess.run([sys.executable, str(inspect_script)], cwd=str(project_root), capture_output=True, text=True)
            print('--- inspect_db.py output ---')
            print(res.stdout)
            if res.stderr:
                print('--- stderr ---')
                print(res.stderr)
        except Exception as e:
            print('Failed to run inspector:', e)

        print('Watcher exiting after one detection.')
        sys.exit(0)

    time.sleep(1.0)

print('Watcher timed out waiting for a new recording')
sys.exit(2)
