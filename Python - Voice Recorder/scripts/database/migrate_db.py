#!/usr/bin/env python3
"""
Database migration runner for Voice Recorder Pro.

This script handles database schema migrations safely.
"""
import sys
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
from alembic.config import Config
from alembic import command

# Setup logging
from core.logging_config import setup_application_logging, get_logger
setup_application_logging("INFO")
logger = get_logger("database.migration")


def backup_database(db_path: Path) -> Optional[Path]:
    """Create a backup of the database before migration."""
    if not db_path.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"app_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    logger.info(f"✓ Database backed up to: {backup_path}")
    return backup_path


def run_migrations():
    """Run database migrations safely."""
    # Get project root
    project_root = Path(__file__).parent
    db_path = project_root / "db" / "app.db"
    
    logger.info("🔄 Voice Recorder Pro - Database Migration")
    logger.info(f"Database: {db_path}")
    
    # Create backup if database exists
    if db_path.exists():
        backup_path = backup_database(db_path)
        if backup_path:
            logger.info(f"📦 Backup created: {backup_path.name}")
    else:
        logger.info("📝 Creating new database")
    
    # Configure Alembic
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    
    try:
        # Run migrations
        logger.info("⚡ Running migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations completed successfully!")
        
        # Show current version
        from alembic.runtime import migration
        from sqlalchemy import create_engine
        
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            context = migration.MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            logger.info(f"📊 Current schema version: {current_rev}")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        backup_path = None  # Initialize for safety
        if 'backup_path' in locals() and backup_path and backup_path.exists():
            logger.info(f"💾 Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
            logger.info("✅ Database restored from backup")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
