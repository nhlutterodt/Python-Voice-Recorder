import os
import sqlite3
import sys
sys.path.insert(0, os.getcwd())
from models import database as db
from cloud import job_queue_sql as jq

print('models.DATABASE_URL=', db.DATABASE_URL)
print('job_queue_sql.DEFAULT_DB=', repr(jq.DEFAULT_DB))
path = jq.DEFAULT_DB or db.DATABASE_URL.replace('sqlite:///', '')
print('using path:', path)
print('exists:', os.path.exists(path))
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('tables:', cur.fetchall())
conn.close()
