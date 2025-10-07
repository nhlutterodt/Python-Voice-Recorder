#!/usr/bin/env python3
"""Inspect the SQLite DB used by the app and list recordings."""
import os
import sqlite3
from pathlib import Path

# Import models.database to get the DATABASE_URL and engine resolution
try:
    from models import database as mdb
    DATABASE_URL = getattr(mdb, 'DATABASE_URL', None)
except Exception as e:
    DATABASE_URL = None

print('PWD =', Path.cwd())
print('DATABASE_URL (models.database):', DATABASE_URL)

# Try to find db files under project
proj_root = Path(__file__).resolve().parents[1]
db_dir = proj_root / 'db'
print('Project root:', proj_root)
print('DB dir:', db_dir)
if db_dir.exists():
    print('DB files:')
    for p in db_dir.iterdir():
        print(' -', p, p.stat().st_size)
else:
    print('DB dir does not exist')

# If DATABASE_URL is sqlite, derive path
if DATABASE_URL and DATABASE_URL.startswith('sqlite:///'):
    db_path = Path(DATABASE_URL.replace('sqlite:///', ''))
else:
    db_path = db_dir / 'app.db'

print('Resolved DB path to inspect:', db_path)

if not db_path.exists():
    print('DB file not found')
    exit(2)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()
print('Tables:')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(' -', row[0])

try:
    cnt = cur.execute('SELECT count(*) FROM recordings').fetchone()[0]
    print('recordings count:', cnt)
    rows = cur.execute('SELECT id, filename, stored_filename, duration, created_at FROM recordings ORDER BY id DESC LIMIT 10').fetchall()
    for r in rows:
        print('R:', r)
except Exception as e:
    print('Query error:', e)
finally:
    conn.close()
