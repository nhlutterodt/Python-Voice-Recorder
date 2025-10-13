"""Application entrypoint that starts the job worker after creating the UI window.

This module exists to clearly document and encapsulate the sequence:
  1. create QApplication and main window (which constructs managers)
  2. start the job-worker supervisor with the real drive_manager instance
  3. enter the Qt event loop

Keeping this in a separate small module makes packaging entrypoints and tests simpler.
"""
import sys
from PySide6.QtWidgets import QApplication
from pathlib import Path

# Use canonical package-root imports to avoid ambiguous module identities
from voice_recorder.enhanced_main import EnhancedAudioEditor, start_job_worker
from voice_recorder.config_manager import config_manager
from voice_recorder.core.logging_config import setup_application_logging

logger = setup_application_logging("INFO")


def run_app(use_keyring: bool = True) -> int:
    """Create the main window, start the job worker, and run the Qt event loop.

    Args:
        use_keyring: passed through to the EnhancedAudioEditor constructor.

    Returns:
        The QApplication exit code.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Enhanced Voice Recorder")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Voice Recorder Pro")

    window = EnhancedAudioEditor(use_keyring=use_keyring)
    window.show()

    # Start the job worker supervisor with the actual DriveManager instance
    dm = getattr(window, 'drive_manager', None)
    start_job_worker(dm)

    logger.info("Application event loop starting from entrypoint")
    return app.exec()


if __name__ == '__main__':
    sys.exit(run_app())
