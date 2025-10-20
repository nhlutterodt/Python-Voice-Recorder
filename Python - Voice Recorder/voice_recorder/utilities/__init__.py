"""Voice Recorder Utilities Module

Centralized reusable utilities for the Voice Recorder Pro application.
This module provides base classes, patterns, and helpers for audio operations.

Module Organization:
- base.py: Base classes for QThread workers and managers
- strategies.py: Multi-strategy retry pattern executor
- batch_processing.py: Generic batch file processor
- device_management.py: Audio device selection and validation
- file_operations.py: File dialog helpers and utilities
- progress_reporting.py: Progress tracking and reporting (future)

Design Principles:
✓ Complementary to existing utilities (performance_monitor, config_manager, logging_config)
✓ No duplication of existing functionality
✓ Reusable across audio and non-audio modules
✓ Type-hinted for IDE support
✓ Fully documented with docstrings

Existing Utilities (DO NOT DUPLICATE):
- src/performance_monitor.py: Operation timing and benchmarking (@contextmanager, @decorator)
- src/config_manager.py: Configuration management (dataclasses, env variables)
- core/logging_config.py: Centralized logging (get_logger singleton pattern)
- core/error_boundaries.py: Error handling and Sentry integration
- services/recording_utils.py: Pure utility functions (hashing, formatting, filenames)

Example Usage:
    from voice_recorder.utilities import BaseWorkerThread, StrategyExecutor, AudioDeviceManager
    
    class MyAudioWorker(BaseWorkerThread):
        def safe_run(self):
            self.emit_progress(50, "Processing...")
            # Do work here
            # Exceptions are automatically caught and emitted as error_occurred signal
"""

from .base import BaseManager, BaseWorkerThread, ProgressEmitter
from .batch_processing import BatchProcessResult, BatchProcessorThread
from .device_management import AudioDeviceManager
from .file_operations import AudioFileSelector
from .strategies import StrategyExecutor, StrategyResult, retry_with_strategies

__all__ = [
    # Base classes
    "BaseWorkerThread",
    "ProgressEmitter",
    "BaseManager",
    # Strategy pattern
    "StrategyExecutor",
    "StrategyResult",
    "retry_with_strategies",
    # Batch processing
    "BatchProcessorThread",
    "BatchProcessResult",
    # Device management
    "AudioDeviceManager",
    # File operations
    "AudioFileSelector",
]

__version__ = "1.0.0"
__author__ = "Voice Recorder Pro"
