# models/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from voice_recorder.core.logging_config import get_logger
from voice_recorder.core.database_context import DatabaseContextManager, configure_database_engine, get_database_file_info

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

# Import-time trace to help diagnose duplicate-table / MetaData issues during tests
try:
	# Print so pytest capture shows the import order and metadata state
	print(f"[IMPORT TRACE] models.database loaded. Base.metadata id={id(Base.metadata)}; tables={list(Base.metadata.tables.keys())}")
except Exception:
	pass

# Ensure this module is available under both legacy and canonical package names so
# importing via either 'models.database' or 'voice_recorder.models.database' returns
# the same module object and the same Base/MetaData instance. This prevents the
# situation where the same file is imported twice under two module names and two
# separate Base objects are created, which breaks SQLAlchemy table registration.
try:
	import sys
	_self_mod = sys.modules.get(__name__)
	if _self_mod is not None:
		for _alias in ("models.database", "voice_recorder.models.database"):
			existing = sys.modules.get(_alias)
			if existing is not _self_mod:
				sys.modules[_alias] = _self_mod
		# Optional extra trace about aliasing
		try:
			print(f"[IMPORT TRACE] models.database aliases set: models.database -> {id(sys.modules.get('models.database'))}; voice_recorder.models.database -> {id(sys.modules.get('voice_recorder.models.database'))}")
		except Exception:
			pass

		# Wrap metadata create_all/drop_all to trace calls (tests call these directly)
		try:
			_orig_create_all = Base.metadata.create_all
			_orig_drop_all = Base.metadata.drop_all

			def _trace_create_all(bind=None, *args, **kwargs):
				try:
					print(f"[IMPORT TRACE] Base.metadata.create_all called. metadata id={id(Base.metadata)}; bind={getattr(bind, 'url', str(bind))}")
				except Exception:
					pass
				return _orig_create_all(bind=bind, *args, **kwargs)

			def _trace_drop_all(bind=None, *args, **kwargs):
				try:
					print(f"[IMPORT TRACE] Base.metadata.drop_all called. metadata id={id(Base.metadata)}; bind={getattr(bind, 'url', str(bind))}")
				except Exception:
					pass
				return _orig_drop_all(bind=bind, *args, **kwargs)

			Base.metadata.create_all = _trace_create_all  # type: ignore
			Base.metadata.drop_all = _trace_drop_all  # type: ignore
		except Exception:
			pass
except Exception:
	pass
