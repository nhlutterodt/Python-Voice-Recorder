# init_db.py
"""
Database initialization for Voice Recorder Pro.
Uses Alembic migrations for proper schema management.
"""
import sys
from pathlib import Path

# Use canonical imports from the package root. When running locally ensure PYTHONPATH
# includes the project root and app dir so voice_recorder.* imports resolve.
from voice_recorder.core.logging_config import setup_application_logging, get_logger
setup_application_logging("INFO")
logger = get_logger("database.init")

def init_database():
    """Initialize database using Alembic migrations."""
    try:
        # Import and run the migration script (canonical import)
        from voice_recorder.scripts.database.migrate_db import run_migrations
        logger.info("Initializing database with migrations...")
        run_migrations()
        logger.info("Database initialized successfully!")
        return True
    except ModuleNotFoundError as e:
        logger.error("Critical dependency missing for migrations: %s", e)
        return False
    except PermissionError as e:
        logger.error("Permission denied during database initialization: %s", e)
        return False
    except OSError as e:
        logger.error("File system error during initialization: %s", e)
        return False
    except ImportError:
        logger.warning("Migration system not available, falling back to direct table creation...")
        # Fallback to old method if Alembic is not available
        from voice_recorder.models import database as app_db
        Base = getattr(app_db, 'Base', None)
        engine = getattr(app_db, 'engine', None)

        # Import model modules so SQLAlchemy's declarative base knows about them
        try:
            import voice_recorder.models.recording  # noqa: F401
        except ModuleNotFoundError as e:
            logger.error("Critical error: Recording model module not found: %s", e)
            return False
        except Exception as e:
            logger.warning("Failed to import model modules: %s", e)
        
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized with direct table creation.")
            return True
        except PermissionError as e:
            logger.error("Permission denied accessing database: %s", e)
            return False
        except OSError as e:
            logger.error("File system error initializing database: %s", e)
            return False
        except Exception as e:
            logger.error("Database creation failed: %s", e, exc_info=True)
            return False
    except Exception as e:
        logger.error("Failed to initialize database: %s", e, exc_info=True)
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
