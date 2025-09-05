# models/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Allow configuration via environment variable for flexibility and CI/production
# Default to a local sqlite DB at project-root/db/app.db
DEFAULT_DB_URL = "sqlite:///db/app.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# If using a sqlite file URL, ensure the parent directory exists. Resolve
# relative sqlite paths against the project folder (two levels up from this file).
if DATABASE_URL.startswith("sqlite:///"):
	# Extract the path portion after the scheme
	sqlite_path = DATABASE_URL.replace("sqlite:///", "", 1)
	project_root = Path(__file__).resolve().parents[1]
	db_file = (project_root / sqlite_path).resolve()
	db_dir = db_file.parent
	try:
		db_dir.mkdir(parents=True, exist_ok=True)
	except Exception:
		# If we can't create the directory here, let SQLAlchemy raise an error later.
		pass
	# Rebuild DATABASE_URL as an absolute path for SQLAlchemy
	DATABASE_URL = f"sqlite:///{db_file.as_posix()}"

engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()
