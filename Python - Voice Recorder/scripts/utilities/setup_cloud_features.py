#!/usr/bin/env python3
"""
Cloud Features Setup Script for Voice Recorder Pro

This script installs the required dependencies for OAuth Google authentication
and Google Drive integration, then tests the cloud functionality.
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_virtual_environment():
    """Check if we're in a virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
        return True
    else:
        print("⚠️ No virtual environment detected")
        print("💡 Recommendation: Create and activate a virtual environment first:")
        print("   python -m venv venv")
        print("   .\\venv\\Scripts\\activate  # Windows")
        print("   source venv/bin/activate  # macOS/Linux")
        response = input("\n❓ Continue anyway? (y/n): ").lower().strip()
        return response in ['y', 'yes']

def install_cloud_dependencies():
    """Install cloud-related dependencies"""
    requirements_file = Path(__file__).parent / "requirements_cloud.txt"
    
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    # Install requirements
    command = f"pip install -r {requirements_file}"
    return run_command(command, "Installing cloud dependencies")

def test_imports():
    """Test if cloud imports work correctly"""
    print("🧪 Testing cloud module imports...")
    
    try:
        # Test Google API imports
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        print("✅ Google API libraries imported successfully")
        
        # Test cloud module imports
        from cloud.auth_manager import GoogleAuthManager
        from cloud.drive_manager import GoogleDriveManager
        from cloud.feature_gate import FeatureGate
        from cloud.cloud_ui import CloudUI
        print("✅ Cloud modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def create_config_template():
    """Create Google Cloud Console configuration template"""
    config_dir = Path(__file__).parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    template_file = config_dir / "client_secrets_template.json"
    
    if template_file.exists():
        print("ℹ️ Configuration template already exists")
        return True
    
    template_content = """{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "project_id": "voice-recorder-pro",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your-client-secret",
    "redirect_uris": ["http://localhost:8080"]
  }
}"""
    
    try:
        with open(template_file, 'w') as f:
            f.write(template_content)
        print(f"✅ Created configuration template: {template_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to create template: {e}")
        return False

def show_next_steps():
    """Show next steps to complete setup"""
    print("\n" + "="*60)
    print("🎉 CLOUD FEATURES SETUP COMPLETED!")
    print("="*60)
    
    print("\n📋 NEXT STEPS:")
    print("1. 🌐 Go to Google Cloud Console (https://console.cloud.google.com)")
    print("2. 📊 Create a new project or select existing project")
    print("3. 🔧 Enable the following APIs:")
    print("   • Google Drive API")
    print("   • Google People API (for profile info)")
    print("4. 🔐 Create OAuth 2.0 credentials:")
    print("   • Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
    print("   • Choose 'Desktop application'")
    print("   • Download the JSON file")
    print("5. 📁 Rename downloaded file to 'client_secrets.json'")
    print("6. 📂 Place it in the 'config' folder of this project")
    print("7. 🚀 Run Voice Recorder Pro and test cloud features!")
    
    print("\n💡 HELPFUL LINKS:")
    print("• Google Cloud Console: https://console.cloud.google.com")
    print("• OAuth Setup Guide: https://developers.google.com/identity/protocols/oauth2")
    print("• Drive API Guide: https://developers.google.com/drive/api/quickstart/python")
    
    config_path = Path(__file__).parent / "config" / "client_secrets.json"
    print(f"\n📍 Expected config file location: {config_path}")
    
    if config_path.exists():
        print("✅ Configuration file found - You're ready to use cloud features!")
    else:
        print("⚠️ Configuration file missing - Complete steps above to enable cloud features")

def main():
    """Main setup process"""
    print("🚀 VOICE RECORDER PRO - CLOUD FEATURES SETUP")
    print("=" * 50)
    
    # Check virtual environment
    if not check_virtual_environment():
        print("❌ Setup cancelled")
        return
    
    # Install dependencies
    if not install_cloud_dependencies():
        print("❌ Failed to install dependencies")
        return
    
    # Test imports
    if not test_imports():
        print("❌ Import test failed")
        return
    
    # Create config template
    create_config_template()
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
