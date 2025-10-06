"""
Storage Information Service Module - Phase 4 Implementation
Handles storage usage and health information collection
"""

import os
import shutil
import platform
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class StorageInfoCollector:
    """
    Collects storage usage and health information
    
    This class handles:
    - Disk usage information collection
    - Storage health monitoring
    - Cross-platform storage information
    - Performance metrics collection
    """
    
    def __init__(self, base_path: Path):
        """
        Initialize storage information collector
        
        Args:
            base_path: Base path for storage information collection
        """
        self.base_path = Path(base_path)
        self._cache = {}
        self._cache_ttl = 60  # Cache results for 60 seconds
        self._last_update = None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get comprehensive storage information with caching
        
        Returns:
            Dictionary with complete storage information
        """
        # Check cache
        if self._is_cache_valid():
            return self._cache.copy()
        
        # Collect fresh information
        storage_info = self._collect_storage_info()
        
        # Update cache
        self._cache = storage_info
        self._last_update = datetime.now()
        
        return storage_info.copy()
    
    def get_raw_storage_info(self) -> Dict[str, Any]:
        """
        Get raw disk usage information without additional processing
        
        Returns:
            Dictionary with basic disk usage information
        """
        return self._get_disk_usage_info()
    
    def _collect_storage_info(self) -> Dict[str, Any]:
        """Collect comprehensive storage information"""
        info = {}
        
        # Basic disk usage
        info.update(self._get_disk_usage_info())
        
        # Platform information
        info.update(self._get_platform_info())
        
        # Path information
        info.update(self._get_path_info())
        
        # Performance metrics
        info.update(self._get_performance_metrics())
        
        # Health assessment
        info.update(self._assess_storage_health(info))
        
        # Add collection metadata
        info['collection_timestamp'] = datetime.now().isoformat()
        info['collector_version'] = '1.0.0'
        
        return info
    
    def _get_disk_usage_info(self) -> Dict[str, Any]:
        """Get cross-platform disk usage information"""
        try:
            # Ensure base path exists
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Try platform-specific approach first
            if platform.system() != 'Windows':
                try:
                    return self._unix_disk_usage()
                except (OSError, AttributeError):
                    pass
            
            # Fallback to cross-platform approach
            return self._cross_platform_disk_usage()
            
        except Exception as e:
            return {
                'base_path': str(self.base_path),
                'free_mb': 0,
                'used_mb': 0,
                'total_mb': 0,
                'error': f"Failed to get disk usage: {e}"
            }
    
    def _unix_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage using Unix-specific methods"""
        disk_usage = os.statvfs(str(self.base_path))
        
        block_size = disk_usage.f_frsize if disk_usage.f_frsize > 0 else disk_usage.f_bsize
        free_bytes = block_size * disk_usage.f_available
        total_bytes = block_size * disk_usage.f_blocks
        used_bytes = total_bytes - (block_size * disk_usage.f_free)
        
        return {
            'base_path': str(self.base_path),
            'free_mb': free_bytes / (1024 * 1024),
            'used_mb': used_bytes / (1024 * 1024),
            'total_mb': total_bytes / (1024 * 1024),
            'method': 'statvfs',
            'block_size': block_size,
            'inodes_total': disk_usage.f_files,
            'inodes_free': disk_usage.f_favail
        }
    
    def _cross_platform_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage using cross-platform methods"""
        total, used, free = shutil.disk_usage(str(self.base_path))
        
        return {
            'base_path': str(self.base_path),
            'free_mb': free / (1024 * 1024),
            'used_mb': used / (1024 * 1024),
            'total_mb': total / (1024 * 1024),
            'method': 'shutil.disk_usage'
        }
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get platform-specific information"""
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'filesystem_encoding': 'utf-8'  # Default assumption
            }
        }
    
    def _get_path_info(self) -> Dict[str, Any]:
        """Get information about the storage paths"""
        path_info = {
            'path_info': {
                'base_path': str(self.base_path),
                'absolute_path': str(self.base_path.absolute()),
                'exists': self.base_path.exists(),
                'is_directory': self.base_path.is_dir() if self.base_path.exists() else False,
                'is_writable': self._check_write_permission(),
                'parent_exists': self.base_path.parent.exists()
            }
        }
        
        # Add path stats if available
        try:
            if self.base_path.exists():
                stat = self.base_path.stat()
                path_info['path_info'].update({
                    'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'access_time': datetime.fromtimestamp(stat.st_atime).isoformat(),
                    'mode': oct(stat.st_mode),
                    'size_bytes': stat.st_size if self.base_path.is_file() else None
                })
        except OSError:
            path_info['path_info']['stat_error'] = 'Unable to get path statistics'
        
        return path_info
    
    def _check_write_permission(self) -> bool:
        """Check if the path is writable"""
        try:
            if not self.base_path.exists():
                # Check if we can create the directory
                test_path = self.base_path / '.write_test_dir'
                test_path.mkdir(parents=True, exist_ok=True)
                test_path.rmdir()
                return True
            else:
                # Test write permission on existing path
                test_file = self.base_path / '.write_test'
                test_file.touch()
                test_file.unlink()
                return True
        except (OSError, PermissionError):
            return False
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics"""
        return {
            'performance': {
                'cache_ttl_seconds': self._cache_ttl,
                'cache_valid': self._is_cache_valid(),
                'last_update': self._last_update.isoformat() if self._last_update else None,
                'collection_method': 'cached' if self._is_cache_valid() else 'fresh'
            }
        }
    
    def _assess_storage_health(self, storage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall storage health"""
        health_info = {
            'health': {
                'status': 'unknown',
                'issues': [],
                'recommendations': []
            }
        }
        
        try:
            # Check basic health indicators
            storage_info.get('free_mb', 0)
            total_mb = storage_info.get('total_mb', 0)
            
            if total_mb > 0:
                utilization = (storage_info.get('used_mb', 0) / total_mb) * 100
                health_info['health']['utilization_percent'] = utilization
                
                # Assess based on utilization
                if utilization > 95:
                    health_info['health']['status'] = 'critical'
                    health_info['health']['issues'].append('Very high disk utilization')
                    health_info['health']['recommendations'].append('Immediate cleanup required')
                elif utilization > 85:
                    health_info['health']['status'] = 'warning'
                    health_info['health']['issues'].append('High disk utilization')
                    health_info['health']['recommendations'].append('Consider cleanup')
                elif utilization > 70:
                    health_info['health']['status'] = 'caution'
                    health_info['health']['recommendations'].append('Monitor disk usage')
                else:
                    health_info['health']['status'] = 'healthy'
            
            # Check path accessibility
            if not storage_info.get('path_info', {}).get('is_writable', False):
                health_info['health']['status'] = 'error'
                health_info['health']['issues'].append('Path not writable')
                health_info['health']['recommendations'].append('Check permissions')
            
            # Check for errors
            if 'error' in storage_info:
                health_info['health']['status'] = 'error'
                health_info['health']['issues'].append(storage_info['error'])
        
        except Exception as e:
            health_info['health']['status'] = 'error'
            health_info['health']['issues'].append(f'Health assessment failed: {e}')
        
        return health_info
    
    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        if not self._cache or not self._last_update:
            return False
        
        age = (datetime.now() - self._last_update).total_seconds()
        return age < self._cache_ttl
    
    def clear_cache(self):
        """Clear the information cache"""
        self._cache.clear()
        self._last_update = None
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Set cache time-to-live"""
        self._cache_ttl = max(0, ttl_seconds)


class StorageMetrics:
    """
    Provides storage metrics and statistics over time
    
    This class tracks storage metrics over time and provides
    statistical analysis of storage usage patterns.
    """
    
    def __init__(self, info_collector: StorageInfoCollector):
        """
        Initialize storage metrics
        
        Args:
            info_collector: StorageInfoCollector instance to use
        """
        self.info_collector = info_collector
        self._metrics_history = []
        self._max_history = 100  # Keep last 100 measurements
    
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Collect current metrics and add to history
        
        Returns:
            Current metrics with historical context
        """
        # Get current storage info
        current_info = self.info_collector.get_storage_info()
        
        # Extract key metrics
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'free_mb': current_info.get('free_mb', 0),
            'used_mb': current_info.get('used_mb', 0),
            'total_mb': current_info.get('total_mb', 0),
            'utilization_percent': 0
        }
        
        if metrics['total_mb'] > 0:
            metrics['utilization_percent'] = (metrics['used_mb'] / metrics['total_mb']) * 100
        
        # Add to history
        self._metrics_history.append(metrics)
        
        # Trim history if needed
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]
        
        # Add statistical analysis
        metrics['statistics'] = self._calculate_statistics()
        
        return metrics
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from metrics history"""
        if not self._metrics_history:
            return {'error': 'No metrics history available'}
        
        # Extract values for analysis
        free_values = [m['free_mb'] for m in self._metrics_history]
        [m['used_mb'] for m in self._metrics_history]
        util_values = [m['utilization_percent'] for m in self._metrics_history]
        
        stats = {
            'history_count': len(self._metrics_history),
            'free_space': {
                'current': free_values[-1] if free_values else 0,
                'min': min(free_values) if free_values else 0,
                'max': max(free_values) if free_values else 0,
                'avg': sum(free_values) / len(free_values) if free_values else 0
            },
            'utilization': {
                'current': util_values[-1] if util_values else 0,
                'min': min(util_values) if util_values else 0,
                'max': max(util_values) if util_values else 0,
                'avg': sum(util_values) / len(util_values) if util_values else 0
            }
        }
        
        # Calculate trends
        if len(self._metrics_history) >= 2:
            stats['trends'] = {
                'free_space_trend': free_values[-1] - free_values[0],
                'utilization_trend': util_values[-1] - util_values[0]
            }
        
        return stats
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get the full metrics history"""
        return self._metrics_history.copy()
    
    def clear_history(self):
        """Clear the metrics history"""
        self._metrics_history.clear()
    
    def export_metrics(self, format_type: str = 'dict') -> Any:
        """
        Export metrics in specified format
        
        Args:
            format_type: Export format ('dict', 'json', 'csv')
            
        Returns:
            Metrics in specified format
        """
        if format_type == 'dict':
            return {
                'metrics_history': self._metrics_history,
                'statistics': self._calculate_statistics()
            }
        elif format_type == 'json':
            import json
            return json.dumps({
                'metrics_history': self._metrics_history,
                'statistics': self._calculate_statistics()
            }, indent=2)
        elif format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if self._metrics_history:
                fieldnames = self._metrics_history[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in self._metrics_history:
                    # Flatten any nested dictionaries
                    flat_row = {}
                    for key, value in row.items():
                        if isinstance(value, dict):
                            flat_row[key] = str(value)
                        else:
                            flat_row[key] = value
                    writer.writerow(flat_row)
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")


# Convenience functions
def get_storage_info_for_path(path: str) -> Dict[str, Any]:
    """
    Get storage information for a specific path
    
    Args:
        path: Path to analyze
        
    Returns:
        Dictionary with storage information
    """
    collector = StorageInfoCollector(Path(path))
    return collector.get_storage_info()


def create_storage_metrics(path: str) -> StorageMetrics:
    """
    Create storage metrics tracker for a path
    
    Args:
        path: Path to track
        
    Returns:
        StorageMetrics instance
    """
    collector = StorageInfoCollector(Path(path))
    return StorageMetrics(collector)
