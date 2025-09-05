"""
Storage Constraints Module - Phase 3 Implementation
Handles all storage capacity and file constraint validation
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..exceptions import StorageConfigValidationError
from .environment import EnvironmentConfig


@dataclass
class ConstraintConfig:
    """Configuration for storage constraints"""
    min_disk_space_mb: int
    max_file_size_mb: int
    enable_disk_space_check: bool
    retention_days: int
    
    def __post_init__(self):
        """Validate constraint configuration values"""
        if self.min_disk_space_mb <= 0:
            raise ValueError("min_disk_space_mb must be positive")
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.retention_days <= 0:
            raise ValueError("retention_days must be positive")


class StorageConstraints:
    """
    Manages storage capacity and file constraints
    
    This class handles all constraint-related logic including:
    - Disk space validation and monitoring
    - File size constraint checking
    - Storage capacity management
    - Constraint violation detection
    """
    
    def __init__(self, constraint_config: ConstraintConfig):
        """
        Initialize storage constraints
        
        Args:
            constraint_config: Configuration for constraints
        """
        self.config = constraint_config
        self.min_disk_space_mb = constraint_config.min_disk_space_mb
        self.max_file_size_mb = constraint_config.max_file_size_mb
        self.enable_disk_space_check = constraint_config.enable_disk_space_check
        self.retention_days = constraint_config.retention_days
    
    @classmethod
    def from_environment_config(cls, env_config: EnvironmentConfig) -> 'StorageConstraints':
        """Create constraints from environment configuration"""
        constraint_config = ConstraintConfig(
            min_disk_space_mb=env_config.min_disk_space_mb,
            max_file_size_mb=env_config.max_file_size_mb,
            enable_disk_space_check=env_config.enable_disk_space_check,
            retention_days=env_config.retention_days
        )
        return cls(constraint_config)
    
    def validate_constraints_configuration(self) -> Dict[str, Any]:
        """
        Validate the constraint configuration itself
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check for reasonable constraint values
            if self.min_disk_space_mb < 10:
                validation_result['warnings'].append(
                    f"Very low minimum disk space requirement: {self.min_disk_space_mb}MB"
                )
            
            if self.max_file_size_mb > 10000:  # 10GB
                validation_result['warnings'].append(
                    f"Very high maximum file size: {self.max_file_size_mb}MB"
                )
            
            if self.retention_days > 3650:  # 10 years
                validation_result['warnings'].append(
                    f"Very long retention period: {self.retention_days} days"
                )
            
            # Check for constraint conflicts
            if self.max_file_size_mb < self.min_disk_space_mb:
                validation_result['warnings'].append(
                    "Maximum file size is smaller than minimum disk space requirement"
                )
                
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error validating constraints configuration: {e}")
        
        return validation_result
    
    def validate_file_constraints(self, file_path: str) -> Dict[str, Any]:
        """
        Validate file against storage constraints
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'file_path': file_path,
            'file_size_mb': 0.0,
            'constraints_checked': []
        }
        
        if not os.path.exists(file_path):
            validation_result['valid'] = False
            validation_result['errors'].append(f"File does not exist: {file_path}")
            return validation_result
        
        try:
            # Get file size
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            validation_result['file_size_mb'] = file_size_mb
            
            # Check file size constraints
            validation_result['constraints_checked'].append('file_size')
            if file_size_mb > self.max_file_size_mb:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"File size {file_size_mb:.1f}MB exceeds maximum {self.max_file_size_mb}MB"
                )
            elif file_size_mb > self.max_file_size_mb * 0.8:
                validation_result['warnings'].append(
                    f"File size {file_size_mb:.1f}MB is approaching maximum {self.max_file_size_mb}MB"
                )
            
            # Add constraint details to result
            validation_result['applied_constraints'] = {
                'max_file_size_mb': self.max_file_size_mb,
                'min_disk_space_mb': self.min_disk_space_mb,
                'disk_space_check_enabled': self.enable_disk_space_check
            }
                    
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error validating file constraints: {e}")
        
        return validation_result
    
    def validate_disk_space_for_file(self, file_path: str, base_path: Path) -> Dict[str, Any]:
        """
        Validate that there's sufficient disk space for a file
        
        Args:
            file_path: Path to file being validated
            base_path: Base storage path for disk space checking
            
        Returns:
            Dictionary with disk space validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'disk_space_check_enabled': self.enable_disk_space_check,
            'required_space_mb': 0.0,
            'available_space_mb': 0.0
        }
        
        if not self.enable_disk_space_check:
            validation_result['message'] = 'Disk space checking disabled'
            return validation_result
        
        try:
            # Get file size if it exists
            file_size_mb = 0.0
            if os.path.exists(file_path):
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Calculate required space (file size + minimum free space buffer)
            required_space_mb = file_size_mb + self.min_disk_space_mb
            validation_result['required_space_mb'] = required_space_mb
            
            # Get available disk space
            from .storage_info import StorageInfoCollector
            info_collector = StorageInfoCollector(base_path)
            storage_info = info_collector.get_raw_storage_info()
            
            available_space_mb = storage_info['free_mb']
            validation_result['available_space_mb'] = available_space_mb
            
            # Validate disk space
            if available_space_mb < required_space_mb:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Insufficient disk space: {available_space_mb:.1f}MB available, "
                    f"{required_space_mb:.1f}MB required"
                )
            elif available_space_mb < required_space_mb * 1.2:  # 20% buffer warning
                validation_result['warnings'].append(
                    f"Low disk space: {available_space_mb:.1f}MB available, "
                    f"{required_space_mb:.1f}MB required"
                )
                
            validation_result['space_utilization'] = {
                'used_percent': (storage_info['used_mb'] / storage_info['total_mb'] * 100) if storage_info['total_mb'] > 0 else 0,
                'free_percent': (storage_info['free_mb'] / storage_info['total_mb'] * 100) if storage_info['total_mb'] > 0 else 0
            }
                    
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error checking disk space: {e}")
        
        return validation_result
    
    def validate_storage_capacity(self, base_path: Path) -> Dict[str, Any]:
        """
        Validate overall storage capacity and health
        
        Args:
            base_path: Base storage path to validate
            
        Returns:
            Dictionary with storage capacity validation results
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'capacity_info': {},
            'health_status': 'unknown'
        }
        
        try:
            # Get storage information
            from .storage_info import StorageInfoCollector
            info_collector = StorageInfoCollector(base_path)
            storage_info = info_collector.get_raw_storage_info()
            
            validation_result['capacity_info'] = storage_info
            
            # Check minimum disk space requirement
            if self.enable_disk_space_check:
                if storage_info['free_mb'] < self.min_disk_space_mb:
                    validation_result['valid'] = False
                    validation_result['errors'].append(
                        f"Insufficient disk space: {storage_info['free_mb']:.1f}MB available, "
                        f"{self.min_disk_space_mb}MB required minimum"
                    )
                    validation_result['health_status'] = 'critical'
                elif storage_info['free_mb'] < self.min_disk_space_mb * 2:
                    validation_result['warnings'].append(
                        f"Low disk space warning: {storage_info['free_mb']:.1f}MB available"
                    )
                    validation_result['health_status'] = 'warning'
                else:
                    validation_result['health_status'] = 'healthy'
            else:
                validation_result['health_status'] = 'unchecked'
                validation_result['message'] = 'Disk space checking disabled'
            
            # Calculate utilization metrics
            if storage_info['total_mb'] > 0:
                utilization_percent = storage_info['used_mb'] / storage_info['total_mb'] * 100
                validation_result['utilization_percent'] = utilization_percent
                
                if utilization_percent > 95:
                    validation_result['warnings'].append(f"Very high disk utilization: {utilization_percent:.1f}%")
                elif utilization_percent > 85:
                    validation_result['warnings'].append(f"High disk utilization: {utilization_percent:.1f}%")
            
            # Add constraint context
            validation_result['constraint_context'] = {
                'min_disk_space_mb': self.min_disk_space_mb,
                'max_file_size_mb': self.max_file_size_mb,
                'disk_space_check_enabled': self.enable_disk_space_check,
                'retention_days': self.retention_days
            }
                    
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error validating storage capacity: {e}")
            validation_result['health_status'] = 'error'
        
        return validation_result
    
    def get_constraint_summary(self) -> Dict[str, Any]:
        """Get summary of all configured constraints"""
        return {
            'constraints': {
                'min_disk_space_mb': self.min_disk_space_mb,
                'max_file_size_mb': self.max_file_size_mb,
                'retention_days': self.retention_days
            },
            'features': {
                'disk_space_check_enabled': self.enable_disk_space_check
            },
            'validation_info': self.validate_constraints_configuration()
        }


class ConstraintValidator:
    """
    Validates files against storage constraints with enhanced diagnostics
    
    This class provides high-level validation operations that combine
    multiple constraint checks and provide comprehensive validation results.
    """
    
    def __init__(self, constraints: StorageConstraints):
        """
        Initialize constraint validator
        
        Args:
            constraints: StorageConstraints instance to use for validation
        """
        self.constraints = constraints
    
    def validate_file_complete(self, file_path: str, base_path: Path) -> Dict[str, Any]:
        """
        Perform complete validation of a file against all constraints
        
        Args:
            file_path: Path to file to validate
            base_path: Base storage path for context
            
        Returns:
            Dictionary with comprehensive validation results
        """
        validation_result = {
            'file_path': file_path,
            'overall_valid': True,
            'constraint_results': {},
            'warnings': [],
            'errors': [],
            'summary': {}
        }
        
        try:
            # File constraint validation
            file_result = self.constraints.validate_file_constraints(file_path)
            validation_result['constraint_results']['file_constraints'] = file_result
            
            if not file_result['valid']:
                validation_result['overall_valid'] = False
                validation_result['errors'].extend(file_result['errors'])
            validation_result['warnings'].extend(file_result['warnings'])
            
            # Disk space validation
            disk_result = self.constraints.validate_disk_space_for_file(file_path, base_path)
            validation_result['constraint_results']['disk_space'] = disk_result
            
            if not disk_result['valid']:
                validation_result['overall_valid'] = False
                validation_result['errors'].extend(disk_result['errors'])
            validation_result['warnings'].extend(disk_result['warnings'])
            
            # Storage capacity validation
            capacity_result = self.constraints.validate_storage_capacity(base_path)
            validation_result['constraint_results']['storage_capacity'] = capacity_result
            
            if not capacity_result['valid']:
                validation_result['overall_valid'] = False
                validation_result['errors'].extend(capacity_result['errors'])
            validation_result['warnings'].extend(capacity_result['warnings'])
            
            # Generate summary
            validation_result['summary'] = {
                'total_errors': len(validation_result['errors']),
                'total_warnings': len(validation_result['warnings']),
                'constraints_checked': ['file_constraints', 'disk_space', 'storage_capacity'],
                'file_size_mb': file_result.get('file_size_mb', 0),
                'available_space_mb': disk_result.get('available_space_mb', 0),
                'health_status': capacity_result.get('health_status', 'unknown')
            }
            
        except Exception as e:
            validation_result['overall_valid'] = False
            validation_result['errors'].append(f"Validation error: {e}")
            validation_result['summary']['validation_error'] = str(e)
        
        return validation_result
    
    def validate_before_operation(self, operation_type: str, estimated_size_mb: float, base_path: Path) -> Dict[str, Any]:
        """
        Validate constraints before performing a storage operation
        
        Args:
            operation_type: Type of operation ('write', 'copy', 'move', etc.)
            estimated_size_mb: Estimated size of the operation in MB
            base_path: Base storage path
            
        Returns:
            Dictionary with pre-operation validation results
        """
        validation_result = {
            'operation_type': operation_type,
            'estimated_size_mb': estimated_size_mb,
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Check if estimated size exceeds file size limits
            if estimated_size_mb > self.constraints.max_file_size_mb:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Estimated operation size {estimated_size_mb:.1f}MB exceeds "
                    f"maximum file size {self.constraints.max_file_size_mb}MB"
                )
            elif estimated_size_mb > self.constraints.max_file_size_mb * 0.8:
                validation_result['warnings'].append(
                    f"Estimated operation size {estimated_size_mb:.1f}MB is approaching "
                    f"maximum file size {self.constraints.max_file_size_mb}MB"
                )
            
            # Check storage capacity for the operation
            if self.constraints.enable_disk_space_check:
                capacity_result = self.constraints.validate_storage_capacity(base_path)
                
                if capacity_result['valid']:
                    available_mb = capacity_result['capacity_info']['free_mb']
                    required_mb = estimated_size_mb + self.constraints.min_disk_space_mb
                    
                    if available_mb < required_mb:
                        validation_result['valid'] = False
                        validation_result['errors'].append(
                            f"Insufficient space for operation: {available_mb:.1f}MB available, "
                            f"{required_mb:.1f}MB required"
                        )
                    elif available_mb < required_mb * 1.5:  # 50% buffer
                        validation_result['warnings'].append(
                            f"Limited space for operation: {available_mb:.1f}MB available"
                        )
                        validation_result['recommendations'].append(
                            "Consider cleaning up old files before proceeding"
                        )
                else:
                    validation_result['warnings'].extend(capacity_result['errors'])
            
            # Add operation-specific recommendations
            if operation_type in ['write', 'copy']:
                if estimated_size_mb > 100:  # Large file
                    validation_result['recommendations'].append(
                        "Consider using compression for large files"
                    )
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Pre-operation validation error: {e}")
        
        return validation_result


# Convenience function for creating constraints from environment
def create_constraints_from_environment(environment: str) -> StorageConstraints:
    """
    Create storage constraints from environment name
    
    Args:
        environment: Environment name ('development', 'testing', 'production')
        
    Returns:
        StorageConstraints instance configured for the environment
    """
    from .environment import EnvironmentManager
    
    env_manager = EnvironmentManager()
    env_config = env_manager.get_config(environment)
    return StorageConstraints.from_environment_config(env_config)
