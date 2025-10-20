"""Base classes for Voice Recorder utilities.

Provides abstract base classes for QThread workers, managers, and common patterns
used throughout the application.

NO DUPLICATION of existing utilities:
- config_manager.py handles configuration (AppConfig dataclasses)
- logging_config.py handles logging (get_logger singleton pattern)
- error_boundaries.py handles error context and Sentry integration
- performance_monitor.py handles operation measurement (@contextmanager measure_operation)

This module complements those by providing:
- BaseWorkerThread: QThread-based workers with standard signals and error handling
- ProgressEmitter: Mixin for progress signaling (complementary to performance_monitor)
- BaseManager: Base for manager-style QObject classes (not in config_manager)
"""

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)


class BaseWorkerThread(QThread):
    """Abstract base class for QThread-based workers.
    
    Provides standard signal handling and error wrapping for safe worker threads.
    Subclasses should override safe_run() instead of run().
    
    Signals:
        progress_updated: (current: int, message: str) - Progress update
        error_occurred: (error_message: str) - Error occurred in worker
    
    Example:
        class MyWorker(BaseWorkerThread):
            def safe_run(self):
                self.emit_progress(50, "Processing...")
                # Do work here
                # Any exceptions are caught and emitted as error_occurred
    """
    
    progress_updated = Signal(int, str)
    error_occurred = Signal(str)
    
    def __init__(self, operation_name: str = "Operation"):
        """Initialize the base worker thread.
        
        Args:
            operation_name: Name of the operation for logging
        """
        super().__init__()
        self.operation_name = operation_name
        self.is_running = False
    
    def run(self) -> None:
        """Concrete run() implementation - wraps safe_run() with error handling.
        
        DO NOT OVERRIDE - subclasses should override safe_run() instead.
        This handles exception wrapping and signal emission.
        """
        try:
            self.is_running = True
            self.safe_run()
        except Exception as e:
            error_msg = f"{self.operation_name} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.emit_error(error_msg)
        finally:
            self.is_running = False
    
    def safe_run(self) -> None:
        """Override this method in subclasses.
        
        Do your work here. Exceptions are caught by run() and emitted as error_occurred.
        """
        raise NotImplementedError("Subclasses must implement safe_run()")
    
    def emit_progress(self, current: int, message: str = "") -> None:
        """Emit a progress update.
        
        Args:
            current: Progress percentage (0-100) or current step
            message: Human-readable progress message
        """
        self.progress_updated.emit(current, message)
    
    def emit_error(self, error_message: str) -> None:
        """Emit an error message.
        
        Args:
            error_message: Error description
        """
        self.error_occurred.emit(error_message)


class ProgressEmitter:
    """Mixin class for adding progress signals to any class.
    
    Use this when you need progress reporting in a non-QThread class.
    
    Example:
        class MyProcessor(QObject, ProgressEmitter):
            progress_updated = Signal(int, str)
            
            def process(self):
                self.emit_progress(50, "Processing...")
    """
    
    progress_updated = Signal(int, str)
    
    def emit_progress(self, current: int, message: str = "") -> None:
        """Emit a progress update.
        
        Args:
            current: Progress percentage (0-100)
            message: Human-readable message
        """
        self.progress_updated.emit(current, message)


class BaseManager(QObject):
    """Base class for manager-style objects.
    
    Provides common manager functionality and signal support.
    Complements config_manager.py which handles configuration, not management.
    
    This is for runtime managers like device management, state management, etc.
    
    Signals:
        status_changed: (status: str) - Manager status changed
    """
    
    status_changed = Signal(str)
    
    def __init__(self, manager_name: str = "Manager"):
        """Initialize the base manager.
        
        Args:
            manager_name: Name of the manager for logging
        """
        super().__init__()
        self.manager_name = manager_name
        self.is_initialized = False
    
    def emit_status(self, status: str) -> None:
        """Emit a status change.
        
        Args:
            status: New status message
        """
        self.status_changed.emit(status)
