"""
Storage Configuration Orchestrator - Phase B Implementation

This module provides a composition-based orchestrator that manages all storage
configuration components. It implements late imports, graceful fallbacks,
and backward compatibility while providing enhanced API surface.

Author: Assistant
Date: January 2025
Phase: B - Enhanced API Surface Implementation
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class StorageConfigError(Exception):
    """Base exception for storage configuration orchestrator errors."""
    pass

@dataclass
class ComponentAvailability:
    """Tracks availability of modular components."""
    environment: bool = False
    path_management: bool = False
    constraints: bool = False
    storage_info: bool = False
    
    @property
    def fallback_mode(self) -> bool:
        return not all([self.environment, self.path_management, self.constraints, self.storage_info])

class StorageConfig:
    """Storage Configuration Orchestrator"""
    
    def __init__(self, environment: str = "development", base_path: Optional[str] = None, custom_config: Optional[Dict[str, Any]] = None):
        logger.info(f"Initializing StorageConfig for environment: {environment}")
        self.environment = environment
        self._custom_config = custom_config or {}
        self._component_availability = ComponentAvailability()
        
        # Component references
        self._EnvironmentManager = None
        self._EnvironmentConfig = None
        self._StoragePathConfig = None
        self._StoragePathManager = None
        self._StorageConstraints = None
        self._ConstraintValidator = None
        self._StorageInfoCollector = None
        self._StorageMetrics = None
        
        # Configuration objects
        self._env_config = None
        self._path_manager = None
        self._constraints = None
        self._constraint_validator = None
        self._storage_info = None
        self._storage_metrics = None
        
        try:
            self._import_components()
            self._resolve_environment_config()
            self._setup_path_management(base_path)
            self._setup_constraints()
            self._setup_storage_info()
            self._setup_legacy_properties()
            logger.info("StorageConfig initialization completed successfully")
            if self._component_availability.fallback_mode:
                logger.warning(f"Operating in fallback mode. Available components: {self._component_availability}")
        except Exception as e:
            logger.error(f"StorageConfig initialization failed: {e}")
            raise StorageConfigError(f"Failed to initialize StorageConfig: {e}") from e
    
    def _try_import(self, module_name: str, class_name: str):
        """Try to import a class from a module with proper error handling."""
        try:
            # Prefer package-root absolute imports to avoid ambiguity when
            # the application is run as a package or via scripts.
            module = importlib.import_module(f'voice_recorder.services.file_storage.config.{module_name}')
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            try:
                # Fallback to relative import for compatibility in dev/test environments
                module = importlib.import_module(f'.{module_name}', package='services.file_storage.config')
                return getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to import {class_name} from {module_name}: {e}")
                return None

    def _import_components(self) -> None:
        """Import storage configuration components with fallback handling."""
        try:
            # Core environment management
            self._EnvironmentConfig = self._try_import('environment', 'EnvironmentConfig')
            if self._EnvironmentConfig:
                self._component_availability.environment = True
            
            # Path management system
            self._StoragePathConfig = self._try_import('path_management', 'StoragePathConfig')
            if self._StoragePathConfig:
                self._component_availability.path_management = True
            
            # File validation and constraints
            self._StorageConstraints = self._try_import('constraints', 'StorageConstraints')
            if self._StorageConstraints:
                self._component_availability.constraints = True
            
            # Storage information and metadata
            self._StorageInfo = self._try_import('storage_info', 'StorageInfo')
            if self._StorageInfo:
                self._component_availability.storage_info = True
                
        except Exception as e:
            logger.warning(f"Component import failed, using fallback mode: {e}")
            self._component_availability = ComponentAvailability()  # Reset to no components
    
    def _resolve_environment_config(self) -> None:
        """Resolve environment configuration."""
        if self._EnvironmentManager:
            try:
                env_manager = self._EnvironmentManager()
                self._env_config = env_manager.get_config(self.environment, self._custom_config)
            except Exception:
                self._env_config = self._create_fallback_environment_config()
        else:
            self._env_config = self._create_fallback_environment_config()
    
    def _create_fallback_environment_config(self):
        """Create fallback environment configuration."""
        fallback_configs: Dict[str, Dict[str, Union[str, int, bool]]] = {
            'development': {
                'base_subdir': 'recordings_dev',
                'min_disk_space_mb': 50,
                'max_file_size_mb': 500,
                'enable_backup': False,
                'enable_compression': False
            },
            'testing': {
                'base_subdir': 'recordings_test',
                'min_disk_space_mb': 10,
                'max_file_size_mb': 100,
                'enable_backup': False,
                'enable_compression': True
            },
            'production': {
                'base_subdir': 'recordings',
                'min_disk_space_mb': 500,
                'max_file_size_mb': 2000,
                'enable_backup': True,
                'enable_compression': True
            }
        }
        
        config_data: Dict[str, Union[str, int, bool]] = fallback_configs.get(self.environment, fallback_configs['development'])
        if self._custom_config:
            config_data.update(self._custom_config)
        
        class FallbackEnvironmentConfig:
            def __init__(self, config_dict: Dict[str, Any]):
                for key, value in config_dict.items():
                    setattr(self, key, value)
        
        return FallbackEnvironmentConfig(config_data)
    
    def _setup_path_management(self, base_path: Optional[str]) -> None:
        """Setup path management."""
        if base_path:
            self._base_path = Path(base_path)
        else:
            base_subdir = getattr(self._env_config, 'base_subdir', 'recordings')
            self._base_path = Path.cwd() / base_subdir

    def _setup_constraints(self) -> None:
        """Setup storage constraints component if available."""
        if self._component_availability.constraints and self._StorageConstraints:
            try:
                # Prefer constructing from an EnvironmentConfig when supported
                env_cfg = self._env_config
                constructed = False
                if env_cfg is not None and hasattr(self._StorageConstraints, 'from_environment_config'):
                    try:
                        self.constraints = self._StorageConstraints.from_environment_config(env_cfg)
                        constructed = True
                    except Exception:
                        constructed = False

                if not constructed:
                    try:
                        # Try to pass the environment config directly
                        self.constraints = self._StorageConstraints(env_cfg)
                        constructed = True
                    except Exception:
                        constructed = False

                if not constructed:
                    # Last resort: try no-arg constructor
                    try:
                        self.constraints = self._StorageConstraints()
                        constructed = True
                    except Exception:
                        raise

                logger.debug("Storage constraints component initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize constraints component: {e}")
                self.constraints = None
        else:
            self.constraints = None
            logger.debug("Storage constraints component not available, using fallback")

    def _setup_storage_info(self) -> None:
        """Setup storage info component if available."""
        if self._component_availability.storage_info and self._StorageInfo:
            try:
                self.storage_info = self._StorageInfo()
                logger.debug("Storage info component initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize storage info component: {e}")
                self.storage_info = None
        else:
            self.storage_info = None
            logger.debug("Storage info component not available, using fallback")

    def _setup_legacy_properties(self) -> None:
        """Setup legacy properties for backward compatibility."""
        self.raw_recordings_path = self._base_path / 'raw'
        self.edited_recordings_path = self._base_path / 'edited'
        self.temp_path = self._base_path / 'temp'
        enable_backup = getattr(self._env_config, 'enable_backup', False)
        self.backup_path = self._base_path / 'backup' if enable_backup else None
    
    @property
    def base_path(self) -> Path:
        return self._base_path
    
    @property
    def min_disk_space_mb(self) -> int:
        return getattr(self._env_config, 'min_disk_space_mb', 50)
    
    @property
    def max_file_size_mb(self) -> int:
        return getattr(self._env_config, 'max_file_size_mb', 500)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            'environment': self.environment,
            'base_path': str(self.base_path),
            'fallback_mode': self._component_availability.fallback_mode,
            'paths': {
                'raw': str(self.raw_recordings_path),
                'edited': str(self.edited_recordings_path),
                'temp': str(self.temp_path),
                'backup': str(self.backup_path) if self.backup_path else None
            },
            'configuration': {
                'min_disk_space_mb': self.min_disk_space_mb,
                'max_file_size_mb': self.max_file_size_mb,
                'enable_backup': getattr(self._env_config, 'enable_backup', False),
                'enable_compression': getattr(self._env_config, 'enable_compression', False)
            }
        }
    
    # Enhanced API Surface - Phase B Methods
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get comprehensive storage information."""
        if self.storage_info:
            try:
                return self.storage_info.get_storage_info()
            except Exception as e:
                logger.warning(f"Failed to get storage info from component: {e}")
        
        # Fallback implementation (tests expect free_mb/used_mb/total_mb keys)
        return {
            'total_mb': 0.0,
            'free_mb': 0.0,
            'used_mb': 0.0,
            'base_path': str(self.base_path),
            'source': 'fallback'
        }

    # Phase 2 enhanced API compatibility wrappers expected by tests
    @property
    def path_manager(self):
        """Expose path manager instance compatible with Phase 2 tests."""
        if not hasattr(self, '_path_manager') or self._path_manager is None:
            try:
                # Create StoragePathManager from environment config if available
                if self._StoragePathConfig:
                    cfg = self._StoragePathConfig(
                        base_path=self.base_path
                    )
                    from voice_recorder.services.file_storage.config.path_management import StoragePathManager
                    self._path_manager = StoragePathManager(cfg)
                else:
                    self._path_manager = None
            except Exception:
                self._path_manager = None
        return self._path_manager

    def get_enhanced_path_info(self) -> Dict[str, Any]:
        """Enhanced path info expected by Phase 2 tests."""
        pm = self.path_manager
        if pm:
            info = pm.get_path_information()
            # Normalize shape expected by tests
            out = {
                'available': True,
                'enhanced_info': {},
                'validation_results': {},
                'supported_types': [],
            }
            try:
                if isinstance(info, dict):
                    out['enhanced_info'] = info
                else:
                    out['enhanced_info'] = {'paths': str(self.base_path)}
                # Provide supported types
                out['supported_types'] = getattr(pm, 'supported_types', ['raw', 'edited', 'temp', 'backup'])
                # Run a permission validation to include validation results if available
                try:
                    val = self.validate_path_permissions()
                    out['validation_results'] = val
                except Exception:
                    out['validation_results'] = {'valid': False, 'message': 'validation_failed'}
            except Exception:
                out['enhanced_info'] = {'configuration': self.get_configuration_summary()}
            return out
        # Indicate enhanced features not available
        return {'available': False, 'fallback_info': {'base_path': str(self.base_path), 'configuration': self.get_configuration_summary()}}

    def ensure_directories_enhanced(self) -> Dict[str, Any]:
        pm = self.path_manager
        if pm:
            return pm.ensure_directories()
        # fallback behaviour
        self.ensure_directories()
        return {'success': True}

    def get_path_for_type_enhanced(self, path_type: str, filename: Optional[str] = None) -> Dict[str, Any]:
        pm = self.path_manager
        out: Dict[str, Any] = {'storage_type': path_type, 'enhanced': False}
        try:
            if pm:
                path = pm.get_path_for_type(path_type)
                if filename:
                    path = path / filename
                out.update({'path': Path(path), 'enhanced': True, 'enhanced_path': Path(path)})
                # Optionally include validation info
                try:
                    out['validation'] = self.validate_path_permissions()
                except Exception:
                    out['validation'] = {'valid': False}
                return out
            # Fallback to existing method
            base = self.get_path_for_type(path_type, filename)
            out.update({'path': base, 'enhanced': False})
            return out
        except Exception as e:
            return {'error': str(e), 'storage_type': path_type, 'enhanced': False}

    def validate_path_permissions(self) -> Dict[str, Any]:
        """Validate permissions for configured storage paths (Phase 2 API)."""
        try:
            from voice_recorder.services.file_storage.config.path_management import PathValidator
            # Validate base paths via the PathValidator utility
            results = {}
            for name, p in self.get_configuration_summary().get('paths', {}).items():
                if p is None:
                    results[name] = {'valid': False, 'message': 'Path not configured'}
                    continue
                path_obj = Path(p)
                valid, perms, message = PathValidator.validate_path_permissions(path_obj)
                results[name] = {'valid': valid, 'permissions': perms.get_summary() if perms else None, 'message': message}
            overall = all(r['valid'] for r in results.values())
            return {'enhanced': True, 'valid': overall, 'paths_checked': list(results.keys()), 'details': results}
        except Exception as e:
            return {'enhanced': False, 'message': str(e)}

    def validate_file_constraints(self, file_path: str) -> Dict[str, Any]:
        """Expose validate_file_constraints for backward compatibility."""
        if self.constraints:
            try:
                # Some implementations expect constraints to be constructed differently
                if hasattr(self.constraints, 'validate_file_constraints'):
                    return self.constraints.validate_file_constraints(file_path)
                elif hasattr(self.constraints, 'validate_file'):
                    return self.constraints.validate_file(file_path)
            except Exception as e:
                logger.warning(f"Constraints validate_file failed: {e}")

        # Fallback simple validation
        path_obj = Path(file_path)
        return {
            'valid': path_obj.exists(),
            'errors': [] if path_obj.exists() else ['File does not exist'],
            'warnings': [],
            'file_size_mb': path_obj.stat().st_size / (1024*1024) if path_obj.exists() else 0,
            'source': 'fallback'
        }
    
    def validate_file(self, file_path: str, file_type: str = 'audio') -> Dict[str, Any]:
        """Validate file according to storage constraints."""
        if self.constraints:
            try:
                return self.constraints.validate_file(file_path, file_type)
            except Exception as e:
                logger.warning(f"Failed to validate file using component: {e}")
        
        # Fallback implementation
        path_obj = Path(file_path)
        return {
            'valid': path_obj.exists(),
            'errors': [] if path_obj.exists() else ['File does not exist'],
            'warnings': [],
            'file_size_mb': path_obj.stat().st_size / (1024*1024) if path_obj.exists() else 0,
            'source': 'fallback'
        }
    
    def get_path_for_type(self, path_type: str, filename: Optional[str] = None) -> Path:
        """Get path for specific recording type."""
        type_mapping = {
            'raw': self.raw_recordings_path,
            'edited': self.edited_recordings_path,
            'temp': self.temp_path,
            'backup': self.backup_path or self.temp_path
        }
        
        base_path = type_mapping.get(path_type, self.base_path)
        return base_path / filename if filename else base_path
    
    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directories = [
            self.raw_recordings_path,
            self.edited_recordings_path,
            self.temp_path
        ]
        
        if self.backup_path:
            directories.append(self.backup_path)
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise StorageConfigError(f"Cannot create directory {directory}: {e}") from e

    @classmethod
    def from_environment(cls, environment: str, **kwargs: Any) -> 'StorageConfig':
        return cls(environment=environment, **kwargs)
    
    @classmethod
    def get_supported_environments(cls) -> List[str]:
        return ['development', 'testing', 'production']
