# enhanced_main.py
# Entry point for the enhanced voice recorder application

import sys
from PySide6.QtWidgets import QApplication
from enhanced_editor import EnhancedAudioEditor


def main():
    """Main application entry point"""
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Enhanced Voice Recorder")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Voice Recorder Pro")
    
    # Create and show main window
    window = EnhancedAudioEditor()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
