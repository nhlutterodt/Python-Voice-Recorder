#!/usr/bin/env python3
"""
Enhanced Build Script for Voice Recorder Pro
Creates a professional executable with human-friendly naming
"""

import sys
import subprocess
import shutil
import os
import stat
from pathlib import Path
 
import json
import datetime

# Import version information
sys.path.insert(0, str(Path(__file__).parent.parent))
from version import CURRENT_VERSION, get_version_info

class VoiceRecorderBuilder:
    """Professional build system for Voice Recorder Pro with human-friendly names"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.scripts_dir = self.project_root / "scripts"
        self.version_info = get_version_info()
        
        # Human-friendly naming
        self.app_display_name = "Voice Recorder Pro"
        self.exe_name = "VoiceRecorderPro"
        self.version_string = str(CURRENT_VERSION)
        self.build_date = datetime.datetime.now().strftime("%Y-%m-%d")
        # Detect optional UPX availability for the spec
        self.upx_available: bool = shutil.which('upx') is not None
        
    def clean_build(self) -> bool:
        """Clean previous build artifacts"""
        print("🧹 Cleaning build directories...")
        
        directories_to_clean = [
            self.build_dir,
            self.dist_dir,
            self.project_root / "__pycache__",
        ]
        
        def _on_rm_error(func, path, exc_info):
            """Error handler for shutil.rmtree to handle read-only files."""
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception as e:
                print(f"   ⚠️ Failed to remove {path}: {e}")

        for directory in directories_to_clean:
            if directory.exists() and directory.is_dir():
                try:
                    shutil.rmtree(directory, onerror=_on_rm_error)
                    print(f"   ✅ Removed {directory.name}")
                except Exception as e:
                    print(f"   ⚠️ Could not remove {directory}: {e}")
        
        # Clean Python cache files
        for cache_dir in self.project_root.rglob("__pycache__"):
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir, onerror=_on_rm_error)
                    print(f"   ✅ Removed cache: {cache_dir.relative_to(self.project_root)}")
                except Exception as e:
                    print(f"   ⚠️ Could not remove cache {cache_dir}: {e}")
        
        # Clean old spec files
        for spec_file in self.project_root.glob("*.spec"):
            try:
                spec_file.unlink()
                print(f"   ✅ Removed old spec: {spec_file.name}")
            except Exception as e:
                print(f"   ⚠️ Could not remove spec {spec_file.name}: {e}")
            
        print("   🎯 Build environment cleaned!")
        return True
    
    def _check_package_import(self, display_name: str, import_name: str) -> tuple[bool, bool]:
        """
        Check if a package can be imported.
        
        Returns:
            tuple[bool, bool]: (success, is_pydub_audioop_issue)
        """
        try:
            __import__(import_name)
            return True, False
        except ImportError as e:
            # Special handling for pydub audioop issues
            is_pydub_audioop = display_name == 'pydub' and 'audioop' in str(e)
            return False, is_pydub_audioop
    
    def _check_package_group(self, packages: dict[str, str], group_name: str, 
                           icon_success: str = "✅", icon_missing: str = "❌") -> list[str]:
        """
        Check a group of packages and return list of missing ones.
        
        Args:
            packages: Dict mapping display_name -> import_name
            group_name: Human-readable group name for logging
            icon_success: Icon for successful imports
            icon_missing: Icon for missing packages
            
        Returns:
            List of missing package display names
        """
        missing: list[str] = []
        
        for display_name, import_name in packages.items():
            success, is_pydub_audioop = self._check_package_import(display_name, import_name)
            
            if success:
                print(f"   {icon_success} {display_name} ({group_name})")
            elif is_pydub_audioop:
                print(f"   ⚠️ {display_name} (imported but audioop missing; audio features may be limited)")
                missing.append(display_name)  # Mark as non-fatal but still track
            else:
                missing.append(display_name)
                print(f"   {icon_missing} {display_name} ({group_name})")
        
        return missing
    
    def _report_missing_packages(self, missing_required: list[str], missing_cloud: list[str], 
                               missing_build: list[str]) -> bool:
        """
        Report missing packages and return whether build can continue.
        
        Returns:
            bool: True if build can continue, False if critical packages missing
        """
        if missing_required:
            print(f"\n❌ Missing required packages: {', '.join(missing_required)}")
            print("Install with: pip install " + " ".join(missing_required))
            return False
        
        if missing_build:
            print(f"\n⚠️ Missing build packages: {', '.join(missing_build)}")
            print("EXE creation will be disabled")
        
        if missing_cloud:
            print(f"\n⚠️ Missing cloud packages: {', '.join(missing_cloud)}")
            print("Cloud features will be disabled in the build")
        
        return True
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        print("📦 Checking dependencies...")
        
        # Define package groups
        required_packages = {
            "PySide6": "PySide6",
            "pydub": "pydub", 
            "Pillow": "PIL",
            "sounddevice": "sounddevice",
            "sqlalchemy": "sqlalchemy",
            "alembic": "alembic"
        }
        
        cloud_packages = {
            "google-auth": "google.auth",
            "google-auth-oauthlib": "google_auth_oauthlib",
            "google-api-python-client": "googleapiclient"
        }
        
        build_packages = {
            "pyinstaller": "PyInstaller"
        }
        
        # Check each package group
        missing_required = self._check_package_group(required_packages, "REQUIRED", "✅", "❌")
        missing_cloud = self._check_package_group(cloud_packages, "cloud - optional", "✅", "⚠️")
        missing_build = self._check_package_group(build_packages, "for EXE creation", "✅", "⚠️")
        
        # Report results and determine if build can continue
        return self._report_missing_packages(missing_required, missing_cloud, missing_build)
    
    def verify_source_files(self) -> bool:
        """Verify all source files are present"""
        print("🔍 Verifying source files...")
        
        critical_files = [
            "enhanced_main.py",
            "enhanced_editor.py", 
            "version.py",
            "audio_processing.py",
            "audio_recorder.py",
            "config_manager.py",
            "performance_monitor.py",
            "migrate_db.py",
            "alembic.ini"
        ]

        missing_files: list[str] = []
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                print(f"   ❌ Missing: {file_path}")
            else:
                print(f"   ✅ {file_path}")
        
        # Check critical directories
        critical_dirs = ["cloud", "models", "config", "alembic"]
        for dir_name in critical_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_files.append(f"{dir_name}/")
                print(f"   ❌ Missing directory: {dir_name}/")
            else:
                print(f"   ✅ {dir_name}/")
        
        if missing_files:
            print(f"\n❌ Missing critical files/directories: {', '.join(missing_files)}")
            return False
        
        return True
    
    def test_import(self) -> bool:
        """Test that main application can be imported"""
        print("🧪 Testing application imports...")
        
        try:
            # Test main imports
            sys.path.insert(0, str(self.project_root))
            import importlib

            # version is critical
            version = importlib.import_module('version')
            print(f"   ✅ Version: {version.CURRENT_VERSION}")

            # Non-critical imports: allow pydub/audioop failures to be non-fatal
            for mod in ('enhanced_editor', 'audio_processing'):
                try:
                    importlib.import_module(mod)
                    print(f"   ✅ {mod} imports successfully")
                except Exception as e:
                    msg = str(e)
                    if 'pydub' in msg or 'audioop' in msg or 'pyaudioop' in msg:
                        print(f"   ⚠️ {mod} import warning: {e} (audio features may be limited)")
                    else:
                        raise
            
            # Test cloud imports (optional)
            try:
                import cloud.auth_manager
                print("   ✅ Cloud authentication imports successfully")
            except ImportError as e:
                print(f"   ⚠️ Cloud features disabled: {e}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Import test failed: {e}")
            return False
    
    def create_build_info(self) -> None:
        """Create comprehensive build information"""
        print("📝 Creating build information...")
        
        build_info = {
            **self.version_info,
            "build_date": self.build_date,
            "build_time": datetime.datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "executable_name": f"{self.exe_name}.exe",
            "display_name": self.app_display_name,
            "features": {
                "audio_recording": True,
                "audio_editing": True,
                "cloud_integration": True,
                "database_support": True,
                "enhanced_ui": True,
                "performance_monitoring": True
            },
            "build_system": {
                "tool": "PyInstaller",
                "compression": "UPX",
                "bundle_type": "one_dir"
            }
        }
        
        build_info_path = self.project_root / "build_info.json"
        with open(build_info_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Build info saved: {build_info_path.name}")
        
        # Also create a human-readable version
        readme_content = f"""# {self.app_display_name} v{self.version_string}

## Build Information
- **Version**: {self.version_string}
- **Build Date**: {self.build_date}
- **Python Version**: {sys.version.split()[0]}
- **Platform**: {sys.platform}

## Features
- 🎤 Professional Audio Recording
- ✂️ Advanced Audio Editing
- ☁️ Cloud Storage Integration (Google Drive)
- 💾 SQLite Database Support
- 🎨 Enhanced User Interface
- 📊 Performance Monitoring

## Quick Start
1. Run `{self.exe_name}.exe` to start the application
2. Use the interface to record or load audio files
3. Edit audio with trim, volume, and effects
4. Save locally or upload to Google Drive
5. Access your recordings through the database

## System Requirements
- Windows 10/11 (64-bit)
- Microphone (for recording)
- Internet connection (for cloud features)

## Support
For issues or questions, check the documentation or contact support.

---
Built with ❤️ using Python and PyInstaller
"""
        
        readme_path = self.project_root / "README_BUILD.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"   ✅ Build README created: {readme_path.name}")
    
    def create_pyinstaller_spec(self) -> Path:
        """Create optimized PyInstaller specification"""
        print("📦 Creating PyInstaller specification...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for {self.app_display_name} v{self.version_string}
# Generated on {self.build_date}

import sys
from pathlib import Path

block_cipher = None

# Data files to include
added_files = [
    ('config', 'config'),
    ('cloud', 'cloud'),
    ('models', 'models'),
    ('alembic', 'alembic'),
    ('alembic.ini', '.'),
    ('migrate_db.py', '.'),
    ('build_info.json', '.'),
    ('README_BUILD.md', '.'),
]

# Optional data directories (include if they exist)
optional_dirs = ['recordings', 'assets']
for dir_name in optional_dirs:
    dir_path = Path(dir_name)
    if dir_path.exists():
        added_files.append((dir_name, dir_name))

# Analysis of the application
a = Analysis(
    ['enhanced_main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # Core UI
        'PySide6.QtCore',
        'PySide6.QtWidgets', 
        'PySide6.QtMultimedia',
        'PySide6.QtGui',
        'PySide6.QtSvg',
        # Audio processing
        'pydub',
        'pydub.playback',
        'sounddevice',
        'numpy',
            # Ensure plotting library is included if used
            'matplotlib',
            # Pillow (PIL) is used by matplotlib for image backends
            'PIL',
        # Database
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlite3',
        # Database migrations
        'alembic',
        'alembic.runtime',
        'alembic.runtime.migration',
        'alembic.operations',
        'alembic.operations.ops',
        'mako',
        'mako.runtime',
        # Cloud (optional)
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.http',
        # Standard library
        'json',
        'logging',
        'threading',
        'queue',
        'datetime',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
    # 'matplotlib',  # removed from excludes: waveform_viewer imports matplotlib at runtime
    'pandas',
    'scipy',
    # 'PIL',  # Pillow required by matplotlib; do not exclude
        'tkinter',
        'test',
        'unittest',
        'pydoc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if Path('assets/icon.ico').exists() else None,
    version_file=None,  # Could add version info here
)

# Collect all files into distribution directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.exe_name}_v{self.version_string}',
)
'''
        
        spec_path = self.project_root / f"{self.exe_name}.spec"
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"   ✅ PyInstaller spec created: {spec_path.name}")
        return spec_path
    
    def build_executable(self) -> bool:
        """Build the standalone executable"""
        print("🔨 Building standalone executable...")
        
        # Check if PyInstaller is available
        # Prefer checking availability with importlib rather than importing
        try:
            import importlib.util
            spec = importlib.util.find_spec('PyInstaller')
            if spec is None:
                print("   ❌ PyInstaller not available")
                print("   Install with: pip install pyinstaller")
                return False
            else:
                # PyInstaller is available, we'll invoke it via subprocess
                print("   ✅ PyInstaller appears available")
        except Exception:
            print("   ❌ Error while checking for PyInstaller")
            return False
        
        try:
            # Create the spec file
            spec_path = self.create_pyinstaller_spec()
            
            # Run PyInstaller
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                "--log-level", "INFO",
                str(spec_path)
            ]
            
            print(f"   🔧 Running: {' '.join(cmd)}")
            print("   ⏳ This may take several minutes...")
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root, 
                capture_output=True, 
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                print("   ✅ Executable built successfully!")
                
                # Check the output
                dist_folder = self.dist_dir / f"{self.exe_name}_v{self.version_string}"
                exe_path = dist_folder / f"{self.exe_name}.exe"
                
                if exe_path.exists():
                    file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"   📦 Executable: {exe_path.relative_to(self.project_root)}")
                    print(f"   📊 Size: {file_size:.1f} MB")
                    
                    # Create convenient launcher
                    self.create_launcher_scripts(dist_folder)
                    
                    return True
                else:
                    print("   ❌ Executable not found at expected location")
                    return False
            else:
                print("   ❌ PyInstaller failed:")
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ❌ Build timed out (>10 minutes)")
            return False
        except Exception as e:
            print(f"   ❌ Build error: {e}")
            return False
    
    def create_launcher_scripts(self, dist_folder: Path) -> None:
        """Create convenient launcher scripts"""
        print("🚀 Creating launcher scripts...")
        
        exe_name = f"{self.exe_name}.exe"
        folder_name = dist_folder.name
        
        # Windows batch launcher
        batch_content = f'''@echo off
title {self.app_display_name} v{self.version_string}
echo.
echo Starting {self.app_display_name} v{self.version_string}...
echo Build Date: {self.build_date}
echo.

cd /d "%~dp0"
if exist "dist\\{folder_name}\\{exe_name}" (
    echo Loading application...
    start "" "dist\\{folder_name}\\{exe_name}"
    echo Application started successfully!
) else (
    echo ERROR: Application not found!
    echo Expected: dist\\{folder_name}\\{exe_name}
    echo.
    echo Please ensure the application was built correctly.
    pause
)
'''
        
        launcher_path = self.project_root / "Launch_VoiceRecorderPro.bat"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        print(f"   ✅ Main launcher: {launcher_path.name}")
        
        # PowerShell launcher
        ps_content = f'''# {self.app_display_name} v{self.version_string} PowerShell Launcher
# Build Date: {self.build_date}

Write-Host ""
Write-Host "Starting {self.app_display_name} v{self.version_string}..." -ForegroundColor Green
Write-Host "Build Date: {self.build_date}" -ForegroundColor Gray
Write-Host ""

$exePath = Join-Path $PSScriptRoot "dist\\{folder_name}\\{exe_name}"

if (Test-Path $exePath) {{
    Write-Host "Loading application..." -ForegroundColor Yellow
    Start-Process $exePath
    Write-Host "Application started successfully!" -ForegroundColor Green
}} else {{
    Write-Host "ERROR: Application not found!" -ForegroundColor Red
    Write-Host "Expected: $exePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please ensure the application was built correctly." -ForegroundColor Yellow
    Read-Host "Press Enter to continue"
}}
'''
        
        ps_launcher_path = self.project_root / "Launch_VoiceRecorderPro.ps1"
        with open(ps_launcher_path, 'w', encoding='utf-8') as f:
            f.write(ps_content)
        
        print(f"   ✅ PowerShell launcher: {ps_launcher_path.name}")
        
        # Create a README for the distribution
        dist_readme = f"""# {self.app_display_name} v{self.version_string}

## Quick Start
Double-click `{exe_name}` to run the application.

## What's Included
- `{exe_name}` - Main application executable
- `config/` - Configuration files
- `cloud/` - Cloud integration modules  
- `models/` - Database models
- `README_BUILD.md` - Build information

## Features
- Professional audio recording
- Advanced audio editing tools
- Google Drive cloud storage
- SQLite database management
- Enhanced user interface

## System Requirements
- Windows 10/11 (64-bit)
- Microphone for recording
- Internet connection for cloud features

---
Built on {self.build_date}
"""
        
        dist_readme_path = dist_folder / "README.txt"
        with open(dist_readme_path, 'w', encoding='utf-8') as f:
            f.write(dist_readme)
        
        print(f"   ✅ Distribution README: {dist_readme_path.name}")
    
    def build(self) -> bool:
        """Run the complete build process"""
        print(f"🏗️ Building {self.app_display_name} v{self.version_string}")
        print("=" * 60)
        print(f"📅 Build Date: {self.build_date}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print(f"💻 Platform: {sys.platform}")
        print("=" * 60)
        
        build_steps = [
            ("🧹 Clean Build Environment", self.clean_build),
            ("📦 Check Dependencies", self.check_dependencies),
            ("🔍 Verify Source Files", self.verify_source_files),
            ("🧪 Test Imports", self.test_import),
            ("📝 Create Build Info", self.create_build_info),
            ("🔨 Build Executable", self.build_executable)
        ]
        
        for step_name, step_func in build_steps:
            print(f"\n{step_name}")
            print("-" * 40)
            
            try:
                result = step_func()
                if result is False:
                    print(f"\n❌ Build failed at: {step_name}")
                    return False
                    
            except Exception as e:
                print(f"\n❌ Error in {step_name}: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Build completed successfully
        print("\n" + "=" * 60)
        print(f"✅ {self.app_display_name} v{self.version_string} BUILD COMPLETE!")
        print("=" * 60)
        
        self.show_build_summary()
        return True
    
    def show_build_summary(self) -> None:
        """Show build summary and next steps"""
        print("\n🎯 BUILD SUMMARY:")
        print("-" * 30)
        
        # Show created files
        artifacts = [
            ("📦 Executable", f"dist/{self.exe_name}_v{self.version_string}/{self.exe_name}.exe"),
            ("🚀 Main Launcher", "Launch_VoiceRecorderPro.bat"),
            ("💻 PowerShell Launcher", "Launch_VoiceRecorderPro.ps1"), 
            ("📋 Build Info", "build_info.json"),
            ("📖 Build README", "README_BUILD.md")
        ]
        
        for icon, name in artifacts:
            file_path = self.project_root / name.split('/')[-1]
            dist_path = self.project_root / name
            
            if file_path.exists() or dist_path.exists():
                print(f"   ✅ {icon} {name}")
            else:
                print(f"   ⚠️ {icon} {name} (not found)")
        
        print("\n🎯 NEXT STEPS:")
        print("-" * 30)
        print("   1. 🚀 Run: Launch_VoiceRecorderPro.bat")
        print("   2. 🧪 Test all features (recording, editing, cloud)")
        print("   3. 📤 Distribute the entire 'dist' folder to users")
        print("   4. 📋 Share README_BUILD.md with users")
        
        # Show file sizes
        dist_folder = self.dist_dir / f"{self.exe_name}_v{self.version_string}"
        if dist_folder.exists():
            total_size = sum(f.stat().st_size for f in dist_folder.rglob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            print(f"\n📊 Total Distribution Size: {total_size_mb:.1f} MB")
        
        print(f"\n🎉 Ready to share {self.app_display_name} v{self.version_string}!")

def main():
    """Main build entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        builder = VoiceRecorderBuilder()
        builder.clean_build()
        print("✅ Clean completed")
        return
    
    builder = VoiceRecorderBuilder()
    success = builder.build()
    
    if success:
        print("\n🎊 BUILD SUCCESSFUL! 🎊")
    else:
        print("\n💥 BUILD FAILED! 💥")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
