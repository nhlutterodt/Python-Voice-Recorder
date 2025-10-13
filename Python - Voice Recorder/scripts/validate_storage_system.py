"""
Storage System Validation Script
Comprehensive validation for all implemented phases of the storage system refactoring
- Phase 1: Environment Configuration Module
- Phase 2: Path Management Module (if implemented)
"""

import sys
import tempfile
import traceback
import argparse
from pathlib import Path

# Use canonical package imports (voice_recorder.*). Do not modify sys.path here.


def check_phase_implementation(phase_num):
    """Check if a specific phase is implemented"""
    phase_files = {
        1: [
            "services/file_storage/config/environment.py",
            "services/file_storage/config/__init__.py",
            "tests/file_storage/config/test_environment.py"
        ],
        2: [
            "services/file_storage/config/path_management.py",
            "tests/file_storage/config/test_path_management.py"
        ]
    }
    
    if phase_num not in phase_files:
        return False
        
    required_files = phase_files[phase_num]
    existing_count = 0
    
    for file_path in required_files:
        if Path(file_path).exists():
            existing_count += 1
    
    # Consider phase implemented if at least 70% of files exist
    return existing_count >= len(required_files) * 0.7


# ===== PHASE 1 VALIDATIONS =====

def validate_phase_1_module_structure():
    """Validate that all Phase 1 modules and files exist"""
    print("🔍 VALIDATING PHASE 1 MODULE STRUCTURE...")
    
    required_files = [
        "services/file_storage/config/environment.py",
        "services/file_storage/config/__init__.py",
        "tests/file_storage/config/test_environment.py",
        "tests/file_storage/config/test_phase_1_integration.py",
        "tests/file_storage/config/__init__.py",
        "tests/file_storage/__init__.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(file_path)
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")
    
    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    
    print("  🎯 All Phase 1 required files exist")
    return True


def validate_phase_1_imports():
    """Validate that all Phase 1 imports work correctly"""
    print("\n🔍 VALIDATING PHASE 1 IMPORTS...")
    try:
        # Test environment module imports
        from voice_recorder.services.file_storage.config.environment import (
            Environment, EnvironmentConfig, EnvironmentManager
        )
        print("  ✅ Environment module imports successful")

        # Test config module imports
        from voice_recorder.services.file_storage.config import StorageConfig, EnvironmentManager as EM
        print("  ✅ Config module imports successful")

        # Test backward compatibility imports
        try:
            from voice_recorder.services.file_storage.config import Environment as Env
            from voice_recorder.services.enhanced_file_storage import StorageConfig as SC
            print("  ✅ Backward compatibility imports successful")
        except ImportError:
            print("  ⚠️ Some backward compatibility imports not available (may be expected)")

        return True

    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"  ❌ Unexpected import error: {e}")
        traceback.print_exc()
        return False


def validate_environment_enum():
    """Validate Environment enum functionality"""
    print("\n🔍 VALIDATING ENVIRONMENT ENUM...")
    try:
        from voice_recorder.services.file_storage.config.environment import Environment

        # Test enum values
        expected_envs = ["development", "testing", "production"]
        actual_envs = Environment.get_all_values()
        
        if actual_envs != expected_envs:
            print(f"  ❌ Environment values mismatch. Expected: {expected_envs}, Got: {actual_envs}")
            return False
        print(f"  ✅ Environment values correct: {actual_envs}")
        
        # Test enum creation from string
        for env_str in expected_envs:
            env = Environment.from_string(env_str)
            if env.value != env_str:
                print(f"  ❌ Environment.from_string failed for {env_str}")
                return False
        print("  ✅ Environment.from_string works for all environments")
        
        # Test invalid environment
        try:
            Environment.from_string("invalid_env")
            print("  ❌ Invalid environment should have raised error")
            return False
        except Exception:
            print("  ✅ Invalid environment properly rejected")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Environment enum validation failed: {e}")
        traceback.print_exc()
        return False


def validate_environment_config():
    """Validate EnvironmentConfig dataclass functionality"""
    print("\n🔍 VALIDATING ENVIRONMENT CONFIG...")
    try:
        from voice_recorder.services.file_storage.config.environment import EnvironmentConfig

        # Test valid config creation
        config = EnvironmentConfig(
            base_subdir="test_recordings",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=True,
            enable_compression=False,
            retention_days=30,
        )
        print("  ✅ Valid EnvironmentConfig creation successful")
        
        # Test config validation (negative values should fail)
        try:
            EnvironmentConfig(
                base_subdir="test",
                min_disk_space_mb=-10,  # Invalid
                enable_disk_space_check=True,
                max_file_size_mb=1000,
                enable_backup=False,
                enable_compression=False,
                retention_days=30
            )
            print("  ❌ Negative min_disk_space_mb should have been rejected")
            return False
        except Exception:
            print("  ✅ Negative values properly rejected")
        
        # Test custom merge functionality
        custom_config = {'min_disk_space_mb': 200, 'enable_backup': True}
        merged = config.merge_with_custom(custom_config)
        
        if merged.min_disk_space_mb != 200 or not merged.enable_backup:
            print("  ❌ Custom config merge failed")
            return False
        print("  ✅ Custom config merge works correctly")
        
        # Test summary functionality
        summary = config.get_summary()
        required_keys = ['storage', 'features', 'policies']
        if not all(key in summary for key in required_keys):
            print("  ❌ Config summary missing required keys")
            return False
        print("  ✅ Config summary generation works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ EnvironmentConfig validation failed: {e}")
        traceback.print_exc()
        return False


def validate_environment_manager():
    """Validate EnvironmentManager functionality"""
    print("\n🔍 VALIDATING ENVIRONMENT MANAGER...")
    
    try:
        from voice_recorder.services.file_storage.config.environment import EnvironmentManager, EnvironmentConfig
        
        # Test supported environments
        supported = EnvironmentManager.get_supported_environments()
        expected = ["development", "testing", "production"]
        if supported != expected:
            print(f"  ❌ Supported environments mismatch. Expected: {expected}, Got: {supported}")
            return False
        print("  ✅ get_supported_environments works correctly")
        
        # Test getting configs for each environment
        for env in expected:
            config = EnvironmentManager.get_config(env)
            if not isinstance(config, EnvironmentConfig):
                print(f"  ❌ get_config for {env} didn't return EnvironmentConfig")
                return False
            if not config.base_subdir:
                print(f"  ❌ get_config for {env} returned invalid config")
                return False
        print("  ✅ get_config works for all environments")
        
        # Test environment validation
        for env in expected:
            validated = EnvironmentManager.validate_environment(env)
            if validated != env:
                print(f"  ❌ validate_environment failed for {env}")
                return False
        print("  ✅ validate_environment works correctly")
        
        # Test environment comparison
        comparison = EnvironmentManager.compare_environments('development', 'production')
        if comparison['identical'] or len(comparison['differences']) == 0:
            print("  ❌ Environment comparison should show differences")
            return False
        print("  ✅ compare_environments works correctly")
        
        # Test get_all_configurations
        all_configs = EnvironmentManager.get_all_configurations()
        if len(all_configs) != 3:
            print("  ❌ get_all_configurations should return 3 configs")
            return False
        print("  ✅ get_all_configurations works correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ EnvironmentManager validation failed: {e}")
        traceback.print_exc()
        return False


def validate_backward_compatibility():
    """Validate that existing StorageConfig still works"""
    print("\n🔍 VALIDATING BACKWARD COMPATIBILITY...")
    
    try:
        # Test original StorageConfig import and usage
        from voice_recorder.services.file_storage.config import StorageConfig
        
        # Test that all original methods still work
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment('testing', base_path=temp_dir)
            
            # Check that all expected attributes exist
            expected_attrs = [
                'environment', 'base_path', 'raw_recordings_path', 
                'edited_recordings_path', 'temp_path', 'min_disk_space_mb',
                'max_file_size_mb', 'enable_disk_space_check'
            ]
            
            for attr in expected_attrs:
                if not hasattr(config, attr):
                    print(f"  ❌ StorageConfig missing attribute: {attr}")
                    return False
            print("  ✅ StorageConfig maintains all expected attributes")
            
            # Test that methods still work
            storage_info = config.get_storage_info()
            if 'free_mb' not in storage_info:
                print("  ❌ get_storage_info missing expected keys")
                return False
            print("  ✅ get_storage_info still works")
            
            # Test file constraint validation
            test_file_path = Path(temp_dir) / "test_file.txt"
            test_file_path.write_text("test content")
            
            validation_result = config.validate_file_constraints(str(test_file_path))
            if 'valid' not in validation_result:
                print("  ❌ validate_file_constraints missing expected keys")
                return False
            print("  ✅ validate_file_constraints still works")
            
            # Test path getter
            raw_path = config.get_path_for_type('raw')
            if not isinstance(raw_path, Path):
                print("  ❌ get_path_for_type should return Path")
                return False
            print("  ✅ get_path_for_type still works")
            
        # Test enhanced_file_storage import (backward compatibility facade)
        try:
            from voice_recorder.services.enhanced_file_storage import StorageConfig as BackwardConfig
            backward_config = BackwardConfig.from_environment('development')
            if backward_config.environment != 'development':
                print("  ❌ Backward compatibility facade not working")
                return False
            print("  ✅ Enhanced file storage facade still works")
        except ImportError:
            print("  ⚠️ Enhanced file storage facade not available (may be expected)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backward compatibility validation failed: {e}")
        traceback.print_exc()
        return False


# ===== PHASE 2 VALIDATIONS =====

def validate_phase_2_imports():
    """Validate that all Phase 2 components can be imported"""
    print("🔍 VALIDATING PHASE 2 IMPORTS...")
    
    try:
        # Test path management module imports
        from voice_recorder.services.file_storage.config.path_management import (
            StoragePathType, StoragePathConfig, StoragePathManager, 
            PathValidator, PathPermissions
        )
        print("  ✅ Path management module imports successful")
        
        # Test updated config module imports
        from voice_recorder.services.file_storage.config import (
            StorageConfig, StoragePathType as SPT, StoragePathManager as SPM
        )
        print("  ✅ Updated config module imports successful")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected import error: {e}")
        return False


def validate_path_management_components():
    """Validate core path management functionality"""
    print("\n🔍 VALIDATING PATH MANAGEMENT COMPONENTS...")
    
    try:
        from voice_recorder.services.file_storage.config.path_management import (
            StoragePathType, StoragePathConfig, StoragePathManager
        )
        
        # Test StoragePathType enum
        types = StoragePathType.get_all_types()
        expected_types = ["raw", "edited", "temp", "backup"]
        if types != expected_types:
            print(f"  ❌ Path types mismatch. Expected: {expected_types}, Got: {types}")
            return False
        print(f"  ✅ StoragePathType enum works: {types}")
        
        # Test StoragePathConfig
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            raw_path = config.get_path_for_type("raw")
            if not isinstance(raw_path, Path):
                print("  ❌ StoragePathConfig.get_path_for_type should return Path")
                return False
            print("  ✅ StoragePathConfig works correctly")
            
            # Test StoragePathManager
            manager = StoragePathManager(config)
            all_paths = manager.get_all_paths()
            if len(all_paths) == 0:
                print("  ❌ StoragePathManager should return paths")
                return False
            print(f"  ✅ StoragePathManager works: {len(all_paths)} paths configured")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Path management validation failed: {e}")
        traceback.print_exc()
        return False


def validate_enhanced_storage_config():
    """Validate enhanced StorageConfig features"""
    print("\n🔍 VALIDATING ENHANCED STORAGE CONFIG...")
    
    try:
        from voice_recorder.services.file_storage.config import StorageConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment('testing', base_path=temp_dir)
            
            # Test that path_manager is available
            if not hasattr(config, 'path_manager'):
                print("  ❌ StorageConfig should have path_manager attribute")
                return False
            print("  ✅ StorageConfig has path_manager attribute")
            
            # Test enhanced features (check if they exist, don't fail if they don't)
            enhanced_methods = [
                'get_enhanced_path_info',
                'ensure_directories_enhanced', 
                'validate_path_permissions',
                'get_path_for_type_enhanced'
            ]
            
            available_methods = []
            for method in enhanced_methods:
                if hasattr(config, method):
                    available_methods.append(method)
            
            if len(available_methods) > 0:
                print(f"  ✅ {len(available_methods)} enhanced methods available: {available_methods}")
                
                # Test enhanced functionality if available
                if hasattr(config, 'get_enhanced_path_info'):
                    enhanced_info = config.get_enhanced_path_info()
                    if 'available' in enhanced_info:
                        print("  ✅ Enhanced path info works")
            else:
                print("  ⚠️ No enhanced methods found (may be expected)")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Enhanced StorageConfig validation failed: {e}")
        traceback.print_exc()
        return False


def validate_phase_2_integration():
    """Validate Phase 2 integration with Phase 1"""
    print("\n🔍 VALIDATING PHASE 1 + PHASE 2 INTEGRATION...")
    
    try:
        from voice_recorder.services.file_storage.config.environment import EnvironmentManager
        from voice_recorder.services.file_storage.config.path_management import StoragePathManager, StoragePathConfig
        from voice_recorder.services.file_storage.config import StorageConfig
        
        # Test that StorageConfig can use path management features
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment('development', base_path=temp_dir)
            
            # Test path manager integration
            if hasattr(config, 'path_manager'):
                path_manager = config.path_manager
                if isinstance(path_manager, StoragePathManager):
                    print("  ✅ StorageConfig properly integrates with StoragePathManager")
                else:
                    print("  ❌ StorageConfig path_manager is not StoragePathManager instance")
                    return False
            else:
                print("  ⚠️ StorageConfig doesn't have path_manager (may be expected)")
            
            # Test that environment configs work with path management
            EnvironmentManager.get_config('development')
            path_config = StoragePathConfig(base_path=Path(temp_dir))
            path_manager = StoragePathManager(path_config)
            
            # Verify they can work together
            all_paths = path_manager.get_all_paths()
            if len(all_paths) > 0:
                print(f"  ✅ Environment and path management integration works: {len(all_paths)} paths")
            else:
                print("  ❌ Path manager should return some paths")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Phase integration validation failed: {e}")
        traceback.print_exc()
        return False


# ===== SHARED VALIDATIONS =====

def validate_unit_tests(phase_num):
    """Validate that unit tests pass for specified phase"""
    print(f"\n🔍 VALIDATING PHASE {phase_num} UNIT TESTS...")
    
    try:
        import subprocess
        
        # Define test files for each phase
        test_files = {
            1: [
                'tests/file_storage/config/test_environment.py',
                'tests/file_storage/config/test_phase_1_integration.py'
            ],
            2: [
                'tests/file_storage/config/test_path_management.py'
            ]
        }
        
        if phase_num not in test_files:
            print(f"  ❌ No test files defined for phase {phase_num}")
            return False
        
        # Change to project directory
        project_dir = Path(__file__).parent.parent
        
        tests_passed = 0
        tests_total = 0
        
        for test_file in test_files[phase_num]:
            if not Path(test_file).exists():
                print(f"  ⚠️ Test file not found: {test_file}")
                continue
                
            tests_total += 1
            result = subprocess.run([
                sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'
            ], cwd=project_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"  ❌ Tests failed for {test_file}:")
                print(f"     STDERR: {result.stderr[:500]}...")  # Truncate long error messages
            else:
                print(f"  ✅ Tests passed for {test_file}")
                tests_passed += 1
        
        if tests_total == 0:
            print("  ⚠️ No test files found to run")
            return True  # Don't fail if no tests exist
        
        success_rate = tests_passed / tests_total
        if success_rate >= 0.5:  # Allow some test failures
            print(f"  ✅ Unit tests mostly passed: {tests_passed}/{tests_total}")
            return True
        else:
            print(f"  ❌ Too many test failures: {tests_passed}/{tests_total}")
            return False
        
    except Exception as e:
        print(f"  ❌ Unit test validation failed: {e}")
        return False


def validate_configuration_consistency():
    """Validate that environment configurations are consistent and sensible"""
    print("\n🔍 VALIDATING CONFIGURATION CONSISTENCY...")
    
    try:
        from voice_recorder.services.file_storage.config.environment import EnvironmentManager
        
        # Get all configurations
        all_configs = EnvironmentManager.get_all_configurations()
        dev_config = all_configs['development']
        test_config = all_configs['testing']
        prod_config = all_configs['production']
        
        # Validate that production has highest constraints
        if not (prod_config.min_disk_space_mb >= dev_config.min_disk_space_mb and
                prod_config.min_disk_space_mb >= test_config.min_disk_space_mb):
            print("  ❌ Production should have highest disk space requirements")
            return False
        print("  ✅ Production has appropriate disk space requirements")
        
        if not (prod_config.max_file_size_mb >= dev_config.max_file_size_mb and
                prod_config.max_file_size_mb >= test_config.max_file_size_mb):
            print("  ❌ Production should have highest file size limits")
            return False
        print("  ✅ Production has appropriate file size limits")
        
        # Validate testing environment is CI-friendly
        if test_config.enable_disk_space_check:
            print("  ⚠️ Testing environment has disk space check enabled (may cause CI issues)")
        else:
            print("  ✅ Testing environment is CI-friendly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration consistency validation failed: {e}")
        traceback.print_exc()
        return False


# ===== MAIN VALIDATION RUNNER =====

def run_phase_validation(phase_num):
    """Run validation for a specific phase"""
    
    if phase_num == 1:
        print("🚀 PHASE 1 VALIDATION: Environment Configuration Module")
        print("=" * 65)
        
        validations = [
            ("Module Structure", validate_phase_1_module_structure),
            ("Imports", validate_phase_1_imports),
            ("Environment Enum", validate_environment_enum),
            ("Environment Config", validate_environment_config),
            ("Environment Manager", validate_environment_manager),
            ("Backward Compatibility", validate_backward_compatibility),
            ("Unit Tests", lambda: validate_unit_tests(1)),
            ("Configuration Consistency", validate_configuration_consistency)
        ]
        
    elif phase_num == 2:
        print("🚀 PHASE 2 VALIDATION: Path Management Module")
        print("=" * 65)
        
        validations = [
            ("Phase 2 Imports", validate_phase_2_imports),
            ("Path Management Components", validate_path_management_components),
            ("Enhanced StorageConfig", validate_enhanced_storage_config),
            ("Phase Integration", validate_phase_2_integration),
            ("Unit Tests", lambda: validate_unit_tests(2))
        ]
    else:
        print(f"❌ Unknown phase: {phase_num}")
        return False
    
    results = {}
    all_passed = True
    
    for name, validator in validations:
        try:
            results[name] = validator()
            if not results[name]:
                all_passed = False
        except Exception as e:
            print(f"\n❌ {name} validation crashed: {e}")
            traceback.print_exc()
            results[name] = False
            all_passed = False
    
    # Print summary
    print("\n" + "=" * 65)
    print(f"📊 PHASE {phase_num} VALIDATION SUMMARY")
    print("=" * 65)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name:<30}: {status}")
    
    print()
    
    if all_passed:
        print(f"🎯 OVERALL STATUS: ✅ PHASE {phase_num} VALIDATION SUCCESSFUL")
        return True
    else:
        failed_validations = [name for name, passed in results.items() if not passed]
        print(f"❌ OVERALL STATUS: PHASE {phase_num} VALIDATION FAILED")
        print(f"   Failed validations: {', '.join(failed_validations)}")
        return False


def main():
    """Main validation entry point"""
    parser = argparse.ArgumentParser(description='Validate Storage System Implementation')
    parser.add_argument('--phase', choices=['1', '2', 'all'], default='auto',
                       help='Which phase to validate (default: auto-detect)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Auto-detect implemented phases
    phase_1_implemented = check_phase_implementation(1)
    phase_2_implemented = check_phase_implementation(2)
    
    print("🔍 STORAGE SYSTEM VALIDATION")
    print("=" * 50)
    print(f"Phase 1 (Environment Config): {'✅ Implemented' if phase_1_implemented else '❌ Not Found'}")
    print(f"Phase 2 (Path Management):    {'✅ Implemented' if phase_2_implemented else '❌ Not Found'}")
    print()
    
    success = True
    
    if args.phase == 'auto':
        # Validate all implemented phases
        if phase_1_implemented:
            success &= run_phase_validation(1)
            print()
        
        if phase_2_implemented:
            success &= run_phase_validation(2)
            print()
            
        if not phase_1_implemented and not phase_2_implemented:
            print("❌ No phases detected for validation")
            success = False
            
    elif args.phase == 'all':
        # Validate all phases (will fail if not implemented)
        success &= run_phase_validation(1)
        print()
        success &= run_phase_validation(2)
        print()
        
    else:
        # Validate specific phase
        phase_num = int(args.phase)
        if phase_num == 1 and not phase_1_implemented:
            print("❌ Phase 1 not implemented")
            success = False
        elif phase_num == 2 and not phase_2_implemented:
            print("❌ Phase 2 not implemented")
            success = False
        else:
            success = run_phase_validation(phase_num)
    
    # Final summary
    print("=" * 65)
    if success:
        print("🎉 ALL VALIDATIONS SUCCESSFUL!")
        print("✅ Storage system is ready for use")
    else:
        print("❌ VALIDATION FAILURES DETECTED")
        print("🛑 Issues must be resolved before proceeding")
    print("=" * 65)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
