# enhanced_main.py
# Entry point for the enhanced voice recorder application

import sys
from PySide6.QtWidgets import QApplication
from enhanced_editor import EnhancedAudioEditor
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
