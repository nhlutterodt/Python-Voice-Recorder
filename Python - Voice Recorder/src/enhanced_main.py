# enhanced_main.py
# Entry point for the enhanced voice recorder application

import sys
from PySide6.QtWidgets import QApplication
from enhanced_editor import EnhancedAudioEditor
from models.database import engine, Base
from core.logging_config import setup_application_logging

# Setup application-wide logging
logger = setup_application_logging("INFO")


def main():
    """Main application entry point"""
    logger.info("Starting Enhanced Voice Recorder application")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Enhanced Voice Recorder")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Voice Recorder Pro")
    
    logger.info("Application properties configured")
    
    # Create and show main window
    try:
        # Database creation at startup has been disabled so Alembic can manage schema
        # For local development you can re-enable the call below (uncomment).
        # try:
        #     Base.metadata.create_all(bind=engine)
        #     logger.info("Database tables ensured (create_all completed)")
        # except Exception as e:
        #     logger.warning(f"Could not create database tables on startup: {e}")

        window = EnhancedAudioEditor()
        window.show()
        logger.info("Main window created and displayed")
        
        # Run the application
        logger.info("Application event loop starting")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
