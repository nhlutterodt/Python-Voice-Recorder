#!/usr/bin/env python3
"""
Development helper: import all models and create tables on the configured database.

Run this when developing locally to ensure the app DB has the expected tables.
Prefer using Alembic for production migrations.
"""
from pathlib import Path
import logging

# Import models so they are registered on the declarative Base
from models import recording  # noqa: F401 (module import registers model)
from models import database as mdb
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Using DATABASE_URL=%s", getattr(mdb, "DATABASE_URL", "<unset>"))
    logger.info("Registering models and creating tables (development only).")
    try:
        mdb.Base.metadata.create_all(bind=mdb.engine)
        tables = inspect(mdb.engine).get_table_names()
        logger.info("Created/verified tables: %s", tables)
    except Exception:
        logger.exception("Failed to create tables on %s", getattr(mdb, "DATABASE_URL", "<unset>"))
        raise


if __name__ == "__main__":
    main()
