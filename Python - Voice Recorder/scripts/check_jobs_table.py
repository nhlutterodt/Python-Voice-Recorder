import os
import sqlite3

from voice_recorder.models import database as db
from voice_recorder.cloud import job_queue_sql as jq


def main():
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


if __name__ == '__main__':
	main()
