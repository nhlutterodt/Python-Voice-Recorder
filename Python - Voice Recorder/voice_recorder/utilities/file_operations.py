"""Audio file selection and dialog utilities.

Provides helpers for standard audio file selection dialogs and list widget management.

NO DUPLICATION of existing utilities:
- This module adds standardized file dialogs (not in any existing utility)
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import QFileDialog, QListWidget, QListWidgetItem
from PySide6.QtWidgets import QWidget

from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)

# Standard audio file extensions
AUDIO_EXTENSIONS = (".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a")

# File dialog filter string
AUDIO_FILE_FILTER = (
    "Audio Files (*.wav *.mp3 *.ogg *.flac *.aac *.m4a);;WAV Files (*.wav);;MP3 Files (*.mp3);;All Files (*)"
)


class AudioFileSelector:
    """Static helper class for audio file selection dialogs.
    
    Provides standardized file selection dialogs and UI helpers.
    
    Example:
        # Select single or multiple files
        files = AudioFileSelector.select_audio_files(self, "recordings/raw")
        
        # Select directory and find audio files
        files = AudioFileSelector.select_audio_directory(self, "recordings/raw")
        
        # Populate list widget
        AudioFileSelector.populate_list_widget(my_list_widget, files)
    """
    
    @staticmethod
    def select_audio_files(
        parent: Optional[QWidget] = None,
        start_dir: str = "",
    ) -> List[str]:
        """Open file selection dialog for audio files.
        
        Args:
            parent: Parent widget for dialog
            start_dir: Initial directory to show
        
        Returns:
            List of selected file paths
        """
        try:
            files, _ = QFileDialog.getOpenFileNames(
                parent,
                "Select Audio Files",
                start_dir,
                AUDIO_FILE_FILTER,
            )
            
            if files:
                logger.debug(f"Selected {len(files)} audio files")
            
            return files
        
        except Exception as e:
            logger.error(f"Error in audio file selection: {e}")
            return []
    
    @staticmethod
    def select_audio_directory(
        parent: Optional[QWidget] = None,
        start_dir: str = "",
    ) -> List[str]:
        """Open directory selection dialog and find audio files.
        
        Args:
            parent: Parent widget for dialog
            start_dir: Initial directory to show
        
        Returns:
            List of audio file paths found in directory (recursive)
        """
        try:
            directory = QFileDialog.getExistingDirectory(
                parent,
                "Select Directory with Audio Files",
                start_dir,
            )
            
            if not directory:
                return []
            
            # Find all audio files recursively
            dir_path = Path(directory)
            audio_files = []
            
            for ext in AUDIO_EXTENSIONS:
                # Use glob pattern to find files with extension
                audio_files.extend(dir_path.rglob(f"*{ext}"))
            
            # Convert to strings and sort
            result = sorted([str(f) for f in audio_files])
            
            if result:
                logger.debug(f"Found {len(result)} audio files in {directory}")
            else:
                logger.info(f"No audio files found in {directory}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error selecting audio directory: {e}")
            return []
    
    @staticmethod
    def populate_list_widget(
        list_widget: QListWidget,
        file_paths: List[str],
    ) -> None:
        """Populate a list widget with file items.
        
        Args:
            list_widget: QListWidget to populate
            file_paths: List of file paths to add
        """
        try:
            list_widget.clear()
            
            for file_path in file_paths:
                # Use just filename as display text
                display_text = Path(file_path).name
                
                # Create list item with full path as tooltip
                item = QListWidgetItem(display_text)
                item.setToolTip(file_path)
                
                list_widget.addItem(item)
            
            logger.debug(f"Populated list widget with {len(file_paths)} items")
        
        except Exception as e:
            logger.error(f"Error populating list widget: {e}")
