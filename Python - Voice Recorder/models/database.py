# models/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from core.logging_config import get_logger
from core.database_context import DatabaseContextManager, configure_database_engine, get_database_file_info

logger = get_logger(__name__)

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
		logger.debug(f"Database directory ensured: {db_dir}")
	except PermissionError as e:
		logger.error(f"Permission denied creating database directory {db_dir}: {e}")
		raise
	except OSError as e:
		logger.error(f"OS error creating database directory {db_dir}: {e}")
		raise
	except Exception as e:
		# Fallback for any other unexpected errors
		logger.warning(f"Could not create database directory {db_dir}: {e}. SQLAlchemy will handle this.")
	# Rebuild DATABASE_URL as an absolute path for SQLAlchemy
	DATABASE_URL = f"sqlite:///{db_file.as_posix()}"

engine = create_engine(DATABASE_URL, echo=False, future=True)

# Configure engine with performance optimizations
configure_database_engine(engine)

# Log database information
db_info = get_database_file_info(DATABASE_URL)
logger.info(f"Database configured: {db_info}")

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

# Create database context manager instance
db_context = DatabaseContextManager(SessionLocal)
