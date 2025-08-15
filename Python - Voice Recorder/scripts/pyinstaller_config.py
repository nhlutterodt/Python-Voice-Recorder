# pyinstaller_config.py
# PyInstaller build configuration for Voice Recorder Pro

import os
from pathlib import Path

def get_build_config():
    """Get PyInstaller build configuration"""
    
    # Get project root directory
    project_root = Path(__file__).parent
    
    # Main script to package
    main_script = project_root / "main.py"
    
    # Application metadata
    app_name = "VoiceRecorderPro"
    app_version = "2.0.0"
    
    # Icon path (if available)
    icon_path = project_root / "assets" / "voice_recorder_icon.ico"
    icon_option = f"--icon={icon_path}" if icon_path.exists() else ""
    
    # Data files to include
    data_files = [
        # Include the config directory
        (str(project_root / "config"), "config"),
        # Include the models directory
        (str(project_root / "models"), "models"),
        # Include the assets directory
        (str(project_root / "assets"), "assets"),
    ]
    
    # Hidden imports (modules that PyInstaller might miss)
    hidden_imports = [
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.sql.default_comparator",
        "PySide6.QtCore",
        "PySide6.QtWidgets", 
        "PySide6.QtGui",
        "PySide6.QtMultimedia",
        "sounddevice",
        "numpy",
        "pydub",
        "matplotlib",
        "performance_monitor",
        "audio_processing",
        "audio_recorder"
    ]
    
    # PyInstaller command configuration
    config = {
        "script": str(main_script),
        "name": app_name,
        "onefile": True,  # Create single executable
        "windowed": True,  # No console window
        "icon": str(icon_path) if icon_path.exists() else None,
        "data_files": data_files,
        "hidden_imports": hidden_imports,
        "exclude_modules": ["tkinter", "matplotlib.backends._backend_tk"],
        "version": app_version,
        "distpath": str(project_root / "dist"),
        "workpath": str(project_root / "build"),
        "specpath": str(project_root)
    }
    
    return config

def generate_spec_file():
    """Generate PyInstaller .spec file"""
    config = get_build_config()
    
    # Fix Windows path separators by using raw strings and forward slashes
    script_path = config["script"].replace("\\", "/")
    icon_path = config["icon"].replace("\\", "/") if config["icon"] else None
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-generated PyInstaller spec file for Voice Recorder Pro

block_cipher = None

a = Analysis(
    [r'{script_path}'],
    pathex=[],
    binaries=[],
    datas={config["data_files"]},
    hiddenimports={config["hidden_imports"]},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={config["exclude_modules"]},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{config["name"]}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={f"r'{icon_path}'" if icon_path else "None"},
)
'''
    
    return spec_content

if __name__ == "__main__":
    config = get_build_config()
    print("🔧 PyInstaller Configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
