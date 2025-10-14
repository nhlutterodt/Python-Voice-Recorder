#!/usr/bin/env python3
"""
Simple database initialization for validation purposes
"""

import os
from sqlalchemy import create_engine
from voice_recorder.models import database as app_db
Base = getattr(app_db, 'Base', None)

def create_test_database():
    """Create database tables for testing purposes"""
    try:
        # Create SQLite database in memory for testing
        db_path = os.path.join(os.path.dirname(__file__), 'db', 'app.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        engine = create_engine(f'sqlite:///{db_path}')
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

if __name__ == "__main__":
    create_test_database()
