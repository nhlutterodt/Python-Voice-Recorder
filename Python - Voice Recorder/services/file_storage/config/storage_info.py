"""
Storage Information Module - Refactored for Orchestrator Integration

This module provides a simple, orchestrator-compatible storage information service.
Replaces the over-engineered StorageInfoCollector with a streamlined implementation.

Author: Assistant
Date: January 2025
Status: Refactored for orchestrator compatibility
"""

from __future__ import annotations

import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageInfo:
    """
    Simple storage information provider optimized for orchestrator integration.
    
    This class provides basic storage information without unnecessary complexity.
    Designed to work seamlessly with the Storage Configuration Orchestrator.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize storage info provider.
        
        Args:
            base_path: Base path for storage analysis. If None, uses current directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        logger.debug(f"StorageInfo initialized with base_path: {self.base_path}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get basic storage information for the configured path.
        
        Returns:
            Dictionary containing storage information with guaranteed keys:
            - total_mb: Total disk space in megabytes
            - used_mb: Used disk space in megabytes  
            - free_mb: Free disk space in megabytes
            - base_path: Path being analyzed
            - timestamp: When information was collected
            - status: 'success' or 'error'
            
        On error, includes 'error' key with error message.
        """
        try:
            # Ensure base path exists for accurate measurement
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Get disk usage using cross-platform method
            total, used, free = shutil.disk_usage(self.base_path)
            
            # Convert to megabytes for easier consumption
            info = {
                'total_mb': round(total / (1024 * 1024), 2),
                'used_mb': round(used / (1024 * 1024), 2),
                'free_mb': round(free / (1024 * 1024), 2),
                'base_path': str(self.base_path.absolute()),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            # Add utilization percentage for convenience
            if info['total_mb'] > 0:
                info['utilization_percent'] = round((info['used_mb'] / info['total_mb']) * 100, 2)
            else:
                info['utilization_percent'] = 0
            
            logger.debug(f"Storage info collected successfully: {info['free_mb']:.2f} MB free")
            return info
            
        except Exception as e:
            error_info = {
                'base_path': str(self.base_path),
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': f"Failed to get storage info: {e}",
                'total_mb': 0,
                'used_mb': 0,
                'free_mb': 0,
                'utilization_percent': 0
            }
            logger.error(f"Storage info collection failed for {self.base_path}: {e}")
            return error_info
    
    def get_basic_info(self) -> Dict[str, Any]:
        """
        Get minimal storage information (alias for get_storage_info for compatibility).
        
        Returns:
            Same as get_storage_info() - provided for interface compatibility.
        """
        return self.get_storage_info()
    
    def check_space_available(self, required_mb: float) -> Dict[str, Any]:
        """
        Check if sufficient space is available for a file of given size.
        
        Args:
            required_mb: Required space in megabytes
            
        Returns:
            Dictionary with availability information:
            - sufficient_space: Boolean indicating if space is available
            - free_mb: Available free space
            - required_mb: Requested space
            - margin_mb: How much space would remain (negative if insufficient)
        """
        try:
            storage_info = self.get_storage_info()
            
            if storage_info['status'] == 'error':
                return {
                    'sufficient_space': False,
                    'free_mb': 0,
                    'required_mb': required_mb,
                    'margin_mb': -required_mb,
                    'error': storage_info.get('error', 'Unknown error')
                }
            
            free_mb = storage_info['free_mb']
            margin_mb = free_mb - required_mb
            sufficient = margin_mb >= 0
            
            result = {
                'sufficient_space': sufficient,
                'free_mb': free_mb,
                'required_mb': required_mb,
                'margin_mb': round(margin_mb, 2)
            }
            
            logger.debug(f"Space check: {required_mb} MB required, {free_mb} MB available, sufficient={sufficient}")
            return result
            
        except Exception as e:
            logger.error(f"Space availability check failed: {e}")
            return {
                'sufficient_space': False,
                'free_mb': 0,
                'required_mb': required_mb,
                'margin_mb': -required_mb,
                'error': f"Space check failed: {e}"
            }
    
    def get_path_info(self) -> Dict[str, Any]:
        """
        Get information about the storage path itself.
        
        Returns:
            Dictionary with path information:
            - exists: Whether path exists
            - is_directory: Whether path is a directory
            - is_writable: Whether path is writable
            - absolute_path: Absolute path string
        """
        try:
            info = {
                'exists': self.base_path.exists(),
                'is_directory': self.base_path.is_dir() if self.base_path.exists() else False,
                'absolute_path': str(self.base_path.absolute()),
                'is_writable': self._check_writable()
            }
            
            # Add creation time if available
            if self.base_path.exists():
                try:
                    stat = self.base_path.stat()
                    info['created_time'] = datetime.fromtimestamp(stat.st_ctime).isoformat()
                    info['modified_time'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except OSError:
                    info['stat_error'] = 'Unable to get path statistics'
            
            return info
            
        except Exception as e:
            logger.error(f"Path info collection failed: {e}")
            return {
                'exists': False,
                'is_directory': False,
                'absolute_path': str(self.base_path),
                'is_writable': False,
                'error': f"Path info failed: {e}"
            }
    
    def _check_writable(self) -> bool:
        """
        Check if the path is writable by attempting to create a test file.
        
        Returns:
            True if path is writable, False otherwise
        """
        try:
            if not self.base_path.exists():
                # Try to create the directory structure
                self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permission with a temporary file
            test_file = self.base_path / '.storage_info_write_test'
            test_file.touch()
            test_file.unlink()
            return True
            
        except (OSError, PermissionError):
            return False
    
    def update_base_path(self, new_path: str) -> None:
        """
        Update the base path for storage analysis.
        
        Args:
            new_path: New base path to analyze
        """
        old_path = self.base_path
        self.base_path = Path(new_path)
        logger.info(f"StorageInfo base path updated from {old_path} to {self.base_path}")


# Backward compatibility aliases for existing code
StorageInfoCollector = StorageInfo  # Alias for any existing references


# Convenience functions for direct usage
def get_storage_info_for_path(path: str) -> Dict[str, Any]:
    """
    Get storage information for a specific path (convenience function).
    
    Args:
        path: Path to analyze
        
    Returns:
        Storage information dictionary
    """
    storage_info = StorageInfo(path)
    return storage_info.get_storage_info()


def check_space_for_file(path: str, file_size_mb: float) -> bool:
    """
    Check if sufficient space exists for a file of given size (convenience function).
    
    Args:
        path: Path to check
        file_size_mb: Required file size in megabytes
        
    Returns:
        True if sufficient space available, False otherwise
    """
    storage_info = StorageInfo(path)
    result = storage_info.check_space_available(file_size_mb)
    return result.get('sufficient_space', False)


# Backwards compatibility: some tests and code expect older API names and a StorageMetrics class
try:
    # Import the legacy module if present and expose expected names
    from .storage_info_old import StorageInfoCollector as _LegacyCollector, StorageMetrics as _LegacyMetrics  # type: ignore

    # If legacy implementations exist, prefer them for feature-complete behavior
    StorageInfoCollector = _LegacyCollector  # type: ignore
    StorageMetrics = _LegacyMetrics  # type: ignore
except Exception:
    # If legacy module missing or import fails, keep above defaults
    pass
