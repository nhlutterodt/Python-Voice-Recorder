#!/usr/bin/env python3
"""
Database migration runner for Voice Recorder Pro.

This script handles database schema migrations safely.
"""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from alembic.config import Config
from alembic import command


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database before migration."""
    if not db_path.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"app_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def run_migrations():
    """Run database migrations safely."""
    # Get project root
    project_root = Path(__file__).parent
    db_path = project_root / "db" / "app.db"
    
    print("🔄 Voice Recorder Pro - Database Migration")
    print(f"Database: {db_path}")
    
    # Create backup if database exists
    if db_path.exists():
        backup_path = backup_database(db_path)
        print(f"📦 Backup created: {backup_path.name}")
    else:
        print("📝 Creating new database")
    
    # Configure Alembic
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    
    try:
        # Run migrations
        print("⚡ Running migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
        
        # Show current version
        from alembic.runtime import migration
        from sqlalchemy import create_engine
        
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            context = migration.MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            print(f"📊 Current schema version: {current_rev}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if backup_path and backup_path.exists():
            print(f"💾 Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
            print("✅ Database restored from backup")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
