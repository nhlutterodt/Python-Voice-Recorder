#!/usr/bin/env python3
"""
Test script to demonstrate improved exception handling
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.logging_config import setup_application_logging, get_logger

# Initialize logging
setup_application_logging("INFO")
logger = get_logger("exception_test")

def test_database_exceptions():
    """Test enhanced database exception handling"""
    logger.info("🧪 Testing database exception handling improvements...")
    
    try:
        from models.database import engine, SessionLocal
        logger.info("✅ Database module loaded successfully")
        
        # Test session creation
        session = SessionLocal()
        session.close()
        logger.info("✅ Database session created and closed successfully")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
    except PermissionError as e:
        logger.error(f"❌ Permission error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

def test_config_exceptions():
    """Test enhanced configuration exception handling"""
    logger.info("🧪 Testing configuration exception handling improvements...")
    
    try:
        from config_manager import ConfigManager
        config = ConfigManager()
        config.load_environment()
        logger.info("✅ Configuration loaded successfully")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")

def test_recording_service_exceptions():
    """Test enhanced recording service exception handling"""
    logger.info("🧪 Testing recording service exception handling improvements...")
    
    try:
        from services.recording_service import RecordingService
        service = RecordingService()
        logger.info("✅ Recording service created successfully")
        
        # Test with non-existent file (should raise FileNotFoundError)
        try:
            service.create_from_file("non_existent_file.wav")
        except FileNotFoundError as e:
            logger.info(f"✅ Expected FileNotFoundError caught: {e}")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
    except Exception as e:
        logger.error(f"❌ Service error: {e}")

if __name__ == "__main__":
    logger.info("🚀 Starting Exception Handling Tests")
    logger.info("=" * 50)
    
    test_database_exceptions()
    print()
    
    test_config_exceptions()
    print()
    
    test_recording_service_exceptions()
    print()
    
    logger.info("=" * 50)
    logger.info("🎯 Exception handling tests completed!")
