"""
Shared utilities for the Voice Recorder application.

Provides common base classes and utility functions used across multiple components
to reduce code duplication and promote consistency.
"""

import logging
from pathlib import Path
from typing import Any, List, Optional, Set

from PySide6.QtCore import QThread, pyqtSignal
from PySide6.QtWidgets import QWidget, QFileDialog, QListWidget, QListWidgetItem


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name)


class BaseWorkerThread(QThread):
    """
    Base class for worker threads that run operations off the main thread.
    
    Provides common signals for progress updates and error handling.
    """
    
    progress_updated = pyqtSignal(str)  # For progress messages
    error_occurred = pyqtSignal(str)    # For error messages
    finished_work = pyqtSignal(dict)    # For work results
    
    def __init__(self):
        """Initialize the worker thread."""
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
    
    def run(self):
        """
        Run the worker thread.
        
        This method should be overridden by subclasses to implement
        the actual work to be performed.
        """
        raise NotImplementedError(
            f"Subclass {self.__class__.__name__} must implement run() method"
        )
    
    def emit_progress(self, message: str) -> None:
        """
        Emit a progress update.
        
        Args:
            message: The progress message to emit
        """
        self.progress_updated.emit(message)
        self.logger.info(f"Progress: {message}")
    
    def emit_error(self, message: str) -> None:
        """
        Emit an error message.
        
        Args:
            message: The error message to emit
        """
        self.error_occurred.emit(message)
        self.logger.error(f"Error: {message}")
    
    def emit_finished(self, result: dict[str, Any]) -> None:
        """
        Emit a finished signal with results.
        
        Args:
            result: Dictionary containing the work results
        """
        self.finished_work.emit(result)


class AudioFileSelector:
    """Utility class for selecting and managing audio files in the UI."""
    
    # Supported audio file extensions
    AUDIO_EXTENSIONS = {
        ".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma"
    }
    
    @staticmethod
    def select_audio_files(
        parent: QWidget,
        initial_directory: str = ""
    ) -> Optional[List[str]]:
        """
        Open a file dialog to select audio files.
        
        Args:
            parent: The parent widget for the dialog
            initial_directory: The initial directory to open
            
        Returns:
            List of selected file paths, or None if cancelled
        """
        file_filter = (
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac *.wma);;"
            "All Files (*)"
        )
        
        files, _ = QFileDialog.getOpenFileNames(
            parent,
            "Select Audio Files",
            initial_directory,
            file_filter
        )
        
        return files if files else None
    
    @staticmethod
    def select_audio_directory(
        parent: QWidget,
        initial_directory: str = ""
    ) -> Optional[List[str]]:
        """
        Open a directory dialog and recursively find audio files.
        
        Args:
            parent: The parent widget for the dialog
            initial_directory: The initial directory to open
            
        Returns:
            List of audio file paths found in the directory, or None if cancelled
        """
        directory = QFileDialog.getExistingDirectory(
            parent,
            "Select Directory with Audio Files",
            initial_directory
        )
        
        if not directory:
            return None
        
        # Recursively find audio files in the directory
        audio_files = []
        base_path = Path(directory)
        
        for ext in AudioFileSelector.AUDIO_EXTENSIONS:
            audio_files.extend(
                str(f) for f in base_path.rglob(f"*{ext}")
            )
        
        return audio_files if audio_files else None
    
    @staticmethod
    def populate_list_widget(
        list_widget: QListWidget,
        files: List[str]
    ) -> None:
        """
        Populate a QListWidget with file items.
        
        Args:
            list_widget: The QListWidget to populate
            files: List of file paths to add
        """
        list_widget.clear()
        
        for file_path in files:
            try:
                # Create item with just the filename for display
                display_name = Path(file_path).name
                item = QListWidgetItem(display_name)
                item.setData(256, file_path)  # Store full path in custom data role
                list_widget.addItem(item)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"Failed to add file to list widget: {file_path} - {e}"
                )
    
    @staticmethod
    def get_selected_files_from_widget(
        list_widget: QListWidget
    ) -> List[str]:
        """
        Get the list of file paths from a populated list widget.
        
        Args:
            list_widget: The QListWidget to read from
            
        Returns:
            List of selected file paths
        """
        files = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            file_path = item.data(256)  # Retrieve full path from custom data role
            if file_path:
                files.append(file_path)
        
        return files
    
    @staticmethod
    def get_unique_files(files: List[str]) -> List[str]:
        """
        Remove duplicate file paths from a list while preserving order.
        
        Args:
            files: List of file paths that may contain duplicates
            
        Returns:
            List of unique file paths in original order
        """
        seen: Set[str] = set()
        unique_files = []
        
        for file_path in files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
        
        return unique_files
