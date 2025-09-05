"""
Path Management Module
Provides enhanced path management capabilities for storage configuration
This is a feature addition that enhances existing functionality without replacing it
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Tuple
import os
import stat
import platform

from ..exceptions import StorageConfigValidationError


class StoragePathType(Enum):
    """Enumeration of supported storage path types"""
    RAW = "raw"
    EDITED = "edited"
    TEMP = "temp"
    BACKUP = "backup"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get all available storage path types"""
        return [path_type.value for path_type in cls]
    
    @classmethod
    def from_string(cls, type_str: str) -> 'StoragePathType':
        """Create StoragePathType from string with validation"""
        for path_type in cls:
            if path_type.value == type_str.lower():
                return path_type
        raise ValueError(f"Invalid storage path type '{type_str}'. Valid types: {cls.get_all_types()}")


@dataclass(frozen=True)
class PathPermissions:
    """Immutable data class representing path permissions information"""
    readable: bool
    writable: bool
    executable: bool
    owner_readable: bool
    owner_writable: bool
    owner_executable: bool
    
    def is_fully_accessible(self) -> bool:
        """Check if path has full read/write access"""
        return self.readable and self.writable
    
    def get_summary(self) -> Dict[str, Any]:
        """Get human-readable permissions summary"""
        return {
            'access': 'full' if self.is_fully_accessible() else 'limited',
            'readable': self.readable,
            'writable': self.writable,
            'executable': self.executable,
            'owner_permissions': {
                'read': self.owner_readable,
                'write': self.owner_writable,
                'execute': self.owner_executable
            }
        }


@dataclass(frozen=True)
class StoragePathConfig:
    """Immutable configuration for storage paths with enhanced validation"""
    base_path: Path
    raw_subdir: str = "raw"
    edited_subdir: str = "edited"
    temp_subdir: str = "temp"
    backup_subdir: Optional[str] = "backup"
    enable_backup_path: bool = True
    auto_create_directories: bool = True
    validate_permissions: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        errors = []
        
        # Validate base path
        if not isinstance(self.base_path, Path):
            try:
                object.__setattr__(self, 'base_path', Path(self.base_path))
            except Exception as e:
                errors.append(f"Invalid base_path: {e}")
        
        # Validate subdirectory names
        for subdir_name, subdir_value in [
            ('raw_subdir', self.raw_subdir),
            ('edited_subdir', self.edited_subdir),
            ('temp_subdir', self.temp_subdir)
        ]:
            if not subdir_value or not isinstance(subdir_value, str):
                errors.append(f"{subdir_name} must be a non-empty string")
            elif '/' in subdir_value or '\\' in subdir_value:
                errors.append(f"{subdir_name} cannot contain path separators")
        
        # Validate backup subdirectory if enabled
        if self.enable_backup_path and self.backup_subdir:
            if not isinstance(self.backup_subdir, str):
                errors.append("backup_subdir must be a string when backup is enabled")
            elif '/' in self.backup_subdir or '\\' in self.backup_subdir:
                errors.append("backup_subdir cannot contain path separators")
        
        if errors:
            raise StorageConfigValidationError(f"StoragePathConfig validation failed: {'; '.join(errors)}")
    
    def get_path_for_type(self, path_type: Union[StoragePathType, str]) -> Path:
        """Get full path for a specific storage type"""
        if isinstance(path_type, str):
            path_type = StoragePathType.from_string(path_type)
        
        path_mapping = {
            StoragePathType.RAW: self.base_path / self.raw_subdir,
            StoragePathType.EDITED: self.base_path / self.edited_subdir,
            StoragePathType.TEMP: self.base_path / self.temp_subdir,
            StoragePathType.BACKUP: self.base_path / self.backup_subdir if (self.enable_backup_path and self.backup_subdir) else None
        }
        
        path = path_mapping[path_type]
        
        if path is None and path_type == StoragePathType.BACKUP:
            if not self.enable_backup_path:
                raise ValueError("Backup path is disabled in current configuration")
            else:
                raise ValueError("Backup path is enabled but backup_subdir is not configured")
        
        return path
    
    def get_all_paths(self) -> Dict[str, Path]:
        """Get all configured paths as a dictionary"""
        paths = {}
        for path_type in StoragePathType:
            try:
                paths[path_type.value] = self.get_path_for_type(path_type)
            except ValueError:
                # Skip paths that are not configured (e.g., disabled backup)
                continue
        return paths
    
    def merge_with_custom(self, custom_config: Dict[str, Any]) -> 'StoragePathConfig':
        """Create new config with custom overrides"""
        valid_fields = {
            'raw_subdir', 'edited_subdir', 'temp_subdir', 'backup_subdir',
            'enable_backup_path', 'auto_create_directories', 'validate_permissions'
        }
        
        # Validate custom config keys
        invalid_keys = set(custom_config.keys()) - valid_fields
        if invalid_keys:
            raise StorageConfigValidationError(f"Invalid configuration keys: {invalid_keys}")
        
        # Create new config with merged values
        current_values = {
            'base_path': self.base_path,
            'raw_subdir': self.raw_subdir,
            'edited_subdir': self.edited_subdir,
            'temp_subdir': self.temp_subdir,
            'backup_subdir': self.backup_subdir,
            'enable_backup_path': self.enable_backup_path,
            'auto_create_directories': self.auto_create_directories,
            'validate_permissions': self.validate_permissions
        }
        
        # Apply custom overrides
        current_values.update(custom_config)
        
        return StoragePathConfig(**current_values)


class PathValidator:
    """Enhanced path validation with detailed diagnostics"""
    
    @staticmethod
    def validate_path_exists(path: Path) -> Tuple[bool, str]:
        """Validate that a path exists"""
        try:
            if path.exists():
                return True, f"Path exists: {path}"
            else:
                return False, f"Path does not exist: {path}"
        except OSError as e:
            return False, f"Cannot access path {path}: {e}"
    
    @staticmethod
    def validate_path_permissions(path: Path) -> Tuple[bool, PathPermissions, str]:
        """Validate path permissions with detailed information"""
        try:
            if not path.exists():
                return False, None, f"Cannot check permissions: path does not exist: {path}"
            
            # Get path statistics
            path_stat = path.stat()
            
            # Check basic permissions
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            executable = os.access(path, os.X_OK)
            
            # Check owner permissions
            mode = path_stat.st_mode
            owner_readable = bool(mode & stat.S_IRUSR)
            owner_writable = bool(mode & stat.S_IWUSR)
            owner_executable = bool(mode & stat.S_IXUSR)
            
            permissions = PathPermissions(
                readable=readable,
                writable=writable,
                executable=executable,
                owner_readable=owner_readable,
                owner_writable=owner_writable,
                owner_executable=owner_executable
            )
            
            if permissions.is_fully_accessible():
                message = f"Path has full access: {path}"
            else:
                missing = []
                if not readable:
                    missing.append("read")
                if not writable:
                    missing.append("write")
                message = f"Path has limited access (missing: {', '.join(missing)}): {path}"
            
            return True, permissions, message
            
        except OSError as e:
            return False, None, f"Cannot check permissions for {path}: {e}"
    
    @staticmethod
    def validate_directory_creation(path: Path) -> Tuple[bool, str]:
        """Validate that a directory can be created at the given path"""
        try:
            if path.exists():
                if path.is_dir():
                    return True, f"Directory already exists: {path}"
                else:
                    return False, f"Path exists but is not a directory: {path}"
            
            # Try to create the directory
            path.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions by creating a test file
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            return True, f"Directory created successfully: {path}"
            
        except OSError as e:
            return False, f"Cannot create directory {path}: {e}"
    
    @staticmethod
    def validate_cross_platform_path(path: Path) -> Tuple[bool, str]:
        """Validate path for cross-platform compatibility"""
        issues = []
        path_str = str(path)
        
        # Check for problematic characters
        if platform.system() == "Windows":
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                if char in path_str:
                    issues.append(f"Contains invalid Windows character: '{char}'")
        
        # Check for reserved names on Windows
        if platform.system() == "Windows":
            reserved_names = {
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            }
            for part in path.parts:
                if part.upper() in reserved_names:
                    issues.append(f"Contains Windows reserved name: '{part}'")
        
        # Check path length
        if len(path_str) > 260 and platform.system() == "Windows":
            issues.append(f"Path too long for Windows ({len(path_str)} > 260 characters)")
        
        if issues:
            return False, f"Cross-platform path issues: {'; '.join(issues)}"
        else:
            return True, "Path is cross-platform compatible"


class StoragePathManager:
    """Enhanced path management with comprehensive validation and diagnostics"""
    
    def __init__(self, config: StoragePathConfig):
        """Initialize path manager with configuration"""
        self.config = config
        self._validation_cache: Dict[str, Any] = {}
    
    def get_path_for_type(self, path_type: Union[StoragePathType, str]) -> Path:
        """Get path for storage type with enhanced error handling"""
        try:
            return self.config.get_path_for_type(path_type)
        except Exception as e:
            raise StorageConfigValidationError(f"Failed to get path for type '{path_type}': {e}")
    
    def get_all_paths(self) -> Dict[str, Path]:
        """Get all configured paths"""
        return self.config.get_all_paths()
    
    def get_supported_path_types(self) -> List[str]:
        """Get list of supported path types"""
        return StoragePathType.get_all_types()
    
    def ensure_directories(self, validate_permissions: bool = None) -> Dict[str, Any]:
        """
        Ensure all configured directories exist with enhanced validation
        
        Args:
            validate_permissions: Override config setting for permission validation
            
        Returns:
            Dictionary with creation results and validation information
        """
        if validate_permissions is None:
            validate_permissions = self.config.validate_permissions
        
        results = {
            'success': True,
            'created_directories': [],
            'existing_directories': [],
            'errors': [],
            'warnings': [],
            'permissions': {}
        }
        
        all_paths = self.get_all_paths()
        
        for path_type, path in all_paths.items():
            try:
                # Validate cross-platform compatibility
                is_compatible, compat_message = PathValidator.validate_cross_platform_path(path)
                if not is_compatible:
                    results['warnings'].append(f"{path_type}: {compat_message}")
                
                # Create directory if needed
                if self.config.auto_create_directories:
                    created, create_message = PathValidator.validate_directory_creation(path)
                    if created:
                        if "already exists" in create_message:
                            results['existing_directories'].append(path_type)
                        else:
                            results['created_directories'].append(path_type)
                    else:
                        results['errors'].append(f"{path_type}: {create_message}")
                        results['success'] = False
                        continue
                
                # Validate permissions if requested
                if validate_permissions:
                    perm_valid, permissions, perm_message = PathValidator.validate_path_permissions(path)
                    if perm_valid and permissions:
                        results['permissions'][path_type] = permissions.get_summary()
                        if not permissions.is_fully_accessible():
                            results['warnings'].append(f"{path_type}: {perm_message}")
                    else:
                        results['errors'].append(f"{path_type}: {perm_message}")
                        if not perm_valid:
                            results['success'] = False
                            
            except Exception as e:
                results['errors'].append(f"{path_type}: Unexpected error: {e}")
                results['success'] = False
        
        return results
    
    def validate_path_configuration(self) -> Dict[str, Any]:
        """Comprehensive validation of path configuration"""
        validation_result = {
            'valid': True,
            'paths_checked': 0,
            'paths_valid': 0,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        all_paths = self.get_all_paths()
        validation_result['paths_checked'] = len(all_paths)
        
        for path_type, path in all_paths.items():
            path_details = {
                'path': str(path),
                'exists': False,
                'accessible': False,
                'cross_platform_compatible': False,
                'permissions': None
            }
            
            try:
                # Check existence
                exists, exist_message = PathValidator.validate_path_exists(path)
                path_details['exists'] = exists
                
                # Check cross-platform compatibility
                compatible, compat_message = PathValidator.validate_cross_platform_path(path)
                path_details['cross_platform_compatible'] = compatible
                if not compatible:
                    validation_result['warnings'].append(f"{path_type}: {compat_message}")
                
                # Check permissions if path exists
                if exists:
                    perm_valid, permissions, perm_message = PathValidator.validate_path_permissions(path)
                    path_details['accessible'] = perm_valid
                    if permissions:
                        path_details['permissions'] = permissions.get_summary()
                    
                    if not perm_valid:
                        validation_result['errors'].append(f"{path_type}: {perm_message}")
                        validation_result['valid'] = False
                    elif not permissions.is_fully_accessible():
                        validation_result['warnings'].append(f"{path_type}: Limited access - {perm_message}")
                
                # Count valid paths
                if exists and path_details['accessible'] and compatible:
                    validation_result['paths_valid'] += 1
                
                validation_result['details'][path_type] = path_details
                
            except Exception as e:
                validation_result['errors'].append(f"{path_type}: Validation error: {e}")
                validation_result['valid'] = False
                validation_result['details'][path_type] = path_details
        
        return validation_result
    
    def get_path_information(self) -> Dict[str, Any]:
        """Get comprehensive information about all paths"""
        return {
            'configuration': {
                'base_path': str(self.config.base_path),
                'subdirectories': {
                    'raw': self.config.raw_subdir,
                    'edited': self.config.edited_subdir,
                    'temp': self.config.temp_subdir,
                    'backup': self.config.backup_subdir
                },
                'settings': {
                    'auto_create_directories': self.config.auto_create_directories,
                    'validate_permissions': self.config.validate_permissions,
                    'backup_enabled': self.config.enable_backup_path
                }
            },
            'paths': {path_type: str(path) for path_type, path in self.get_all_paths().items()},
            'supported_types': self.get_supported_path_types(),
            'platform': platform.system()
        }
    
    @classmethod
    def create_default(cls, base_path: Union[str, Path], enable_backup: bool = True) -> 'StoragePathManager':
        """Create a StoragePathManager with default configuration"""
        config = StoragePathConfig(
            base_path=Path(base_path),
            enable_backup_path=enable_backup
        )
        return cls(config)
    
    @classmethod
    def create_from_environment_config(cls, base_path: Union[str, Path], 
                                     environment_config: Dict[str, Any]) -> 'StoragePathManager':
        """Create StoragePathManager from environment configuration"""
        config = StoragePathConfig(
            base_path=Path(base_path),
            enable_backup_path=environment_config.get('enable_backup', True),
            auto_create_directories=True,
            validate_permissions=True
        )
        return cls(config)
