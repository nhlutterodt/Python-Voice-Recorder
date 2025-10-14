# enhanced_main.py
# Entry point for the enhanced voice recorder application

import argparse
import sys
import threading
from typing import Any, Optional

from PySide6.QtWidgets import QApplication

from voice_recorder.config_manager import config_manager

# Defer importing SQLAlchemy engine/Base until runtime to avoid import-time
# side-effects during import-only validation runs.
from voice_recorder.core.logging_config import setup_application_logging

# Support running as a module (python -m src.enhanced_main) and as a
# script by preferring package-relative imports with absolute fallbacks.
from voice_recorder.enhanced_editor import EnhancedAudioEditor


# Import the job supervisor lazily to avoid import-time side effects
def start_job_worker(drive_manager: Any) -> Optional[threading.Thread]:
    """Start the cloud job worker supervisor if enabled in configuration.

    Returns the supervisor Thread object or None. This helper is safe to call
    from the application bootstrap after managers are available.
    """
    try:
        # Respect an explicit opt-out. If config_manager.enable_cloud_job_worker
        # is missing or True, we'll attempt to start the supervisor so queued
        # uploads are processed automatically.
        if getattr(config_manager, "enable_cloud_job_worker", True):
            if drive_manager is None:
                logger.debug("No DriveManager provided; skipping job worker start")
                return None
            # Import the job worker module using the canonical package-root path
            # to avoid ambiguous module identities when running as a script vs
            # package. Keep this import local/lazy to avoid import-time DB side-effects.
            from voice_recorder.cloud.job_queue_sql import run_worker_with_supervisor

            db_path = getattr(config_manager, "cloud_jobs_db_path", None)
            try:
                return run_worker_with_supervisor(drive_manager, db_path=db_path)
            except Exception as e:
                logger.warning(f"Failed to start cloud job supervisor: {e}")
    except Exception:
        logger.debug("Cloud job supervisor not started (config missing or error)")
    return None


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

    # Parse runtime flags
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--no-keyring",
        dest="no_keyring",
        action="store_true",
        help="Disable OS keyring usage for credentials",
    )
    args, _ = parser.parse_known_args()

    # Determine keyring preference: CLI overrides config_manager
    use_keyring = not bool(args.no_keyring) and config_manager.prefers_keyring()

    # Create and show main window
    try:
        # Database creation at startup has been disabled so Alembic can manage schema
        # For local development you can re-enable the call below (uncomment).
        # try:
        #     Base.metadata.create_all(bind=engine)
        #     logger.info("Database tables ensured (create_all completed)")
        # except Exception as e:
        #     logger.warning(f"Could not create database tables on startup: {e}")

        window = EnhancedAudioEditor(use_keyring=use_keyring)
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
