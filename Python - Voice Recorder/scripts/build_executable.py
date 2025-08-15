# build_executable.py
# Build script to create standalone executable using PyInstaller

import subprocess
import sys
import os
from pathlib import Path
from pyinstaller_config import get_build_config, generate_spec_file

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller found: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        return install_pyinstaller()

def install_pyinstaller():
    """Install PyInstaller if not available"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyInstaller: {e}")
        return False

def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = generate_spec_file()
    spec_path = Path("VoiceRecorderPro.spec")
    
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print(f"✅ Spec file created: {spec_path}")
    return spec_path

def build_executable():
    """Build the standalone executable"""
    print("🔨 Building Voice Recorder Pro executable...")
    
    # Check PyInstaller availability
    if not check_pyinstaller():
        return False
    
    # Create spec file
    spec_path = create_spec_file()
    
    # Run PyInstaller
    try:
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_path), "--clean"]
        print(f"🔧 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Build completed successfully!")
            
            # Check if executable was created
            dist_path = Path("dist") / "VoiceRecorderPro.exe"
            if dist_path.exists():
                size_mb = dist_path.stat().st_size / (1024 * 1024)
                print(f"📦 Executable created: {dist_path}")
                print(f"📊 File size: {size_mb:.1f} MB")
                return True
            else:
                print("❌ Executable not found in dist directory")
                return False
        else:
            print("❌ Build failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def create_launch_script():
    """Create a simple launch script for testing"""
    script_content = '''@echo off
echo 🚀 Launching Voice Recorder Pro...
echo.

REM Check if executable exists
if not exist "dist\\VoiceRecorderPro.exe" (
    echo ❌ VoiceRecorderPro.exe not found in dist folder
    echo Please run build_executable.py first
    pause
    exit /b 1
)

REM Launch the application
echo ✅ Starting Voice Recorder Pro...
start "" "dist\\VoiceRecorderPro.exe"

echo 📱 Voice Recorder Pro launched!
echo You can close this window.
timeout 3 >nul
'''
    
    with open("launch_voice_recorder.bat", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ Launch script created: launch_voice_recorder.bat")

def main():
    """Main build process"""
    print("🏗️  Voice Recorder Pro - Executable Builder")
    print("=" * 50)
    
    # Show configuration
    config = get_build_config()
    print("📋 Build Configuration:")
    print(f"  📄 Script: {config['script']}")
    print(f"  📱 App Name: {config['name']}")
    print(f"  🔢 Version: {config['version']}")
    print(f"  🎨 Icon: {config['icon'] or 'Default'}")
    print()
    
    # Build executable
    success = build_executable()
    
    if success:
        print()
        print("🎉 BUILD SUCCESSFUL!")
        print("=" * 50)
        print("📦 Your Voice Recorder Pro executable is ready:")
        print("   📂 Location: dist/VoiceRecorderPro.exe")
        print("   🖱️  Double-click to run")
        print()
        
        # Create launch script
        create_launch_script()
        
        print("🚀 Next Steps:")
        print("   1. Test: Double-click dist/VoiceRecorderPro.exe")
        print("   2. Or use: launch_voice_recorder.bat")
        print("   3. Share: Copy dist/VoiceRecorderPro.exe to other computers")
        print()
        
    else:
        print()
        print("❌ BUILD FAILED!")
        print("=" * 50)
        print("🔧 Troubleshooting:")
        print("   1. Check all dependencies are installed")
        print("   2. Ensure virtual environment is activated")
        print("   3. Review error messages above")

if __name__ == "__main__":
    main()
