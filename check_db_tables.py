import sqlite3, os, sys

db = r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\db\app.db"
print('DB file exists:', os.path.exists(db))
try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    rows = cur.fetchall()
    print('tables:', rows)
finally:
    try:
        conn.close()
    except Exception:
        pass
