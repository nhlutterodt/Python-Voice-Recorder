#!/usr/bin/env python3
"""
Secure Configuration Manager for Voice Recorder Pro
Handles environment variables, secret management, and secure credential loading
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    cloud_features_enabled: bool = True
    local_encryption_enabled: bool = False
    telemetry_enabled: bool = False
    crash_reporting_enabled: bool = False

@dataclass
class GoogleCloudConfig:
    """Google Cloud configuration settings"""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    project_id: Optional[str] = None
    redirect_uri: str = "http://localhost:8080"
    scopes: str = "https://www.googleapis.com/auth/drive.file"

@dataclass
class AppConfig:
    """Main application configuration"""
    name: str = "Voice Recorder Pro"
    version: str = "2.0.0-beta"
    debug: bool = False
    environment: str = "production"
    
    # Paths
    recordings_raw_path: str = "recordings/raw"
    recordings_edited_path: str = "recordings/edited"
    database_url: str = "sqlite:///db/app.db"
    
    # Audio settings
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    audio_format: str = "wav"
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"

class ConfigManager:
    """Secure configuration manager with environment variable support"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.secrets_dir = self.project_root / "config"
        
        # Load configuration
        self.load_environment()
        self.app_config = self._load_app_config()
        self.security_config = self._load_security_config()
        self.google_config = self._load_google_config()
    
    def load_environment(self) -> None:
        """Load environment variables from .env file if it exists"""
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                print("✅ Environment variables loaded from .env")
            except Exception as e:
                print(f"⚠️ Warning: Could not load .env file: {e}")
        else:
            print("ℹ️ No .env file found, using system environment variables")
    
    def _load_app_config(self) -> AppConfig:
        """Load application configuration from environment variables"""
        return AppConfig(
            name=os.getenv("APP_NAME", "Voice Recorder Pro"),
            version=os.getenv("APP_VERSION", "2.0.0-beta"),
            debug=os.getenv("APP_DEBUG", "false").lower() == "true",
            environment=os.getenv("APP_ENVIRONMENT", "production"),
            recordings_raw_path=os.getenv("RECORDINGS_RAW_PATH", "recordings/raw"),
            recordings_edited_path=os.getenv("RECORDINGS_EDITED_PATH", "recordings/edited"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///db/app.db"),
            audio_sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "44100")),
            audio_channels=int(os.getenv("AUDIO_CHANNELS", "2")),
            audio_format=os.getenv("AUDIO_FORMAT", "wav"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
            log_file_path=os.getenv("LOG_FILE_PATH", "logs/app.log")
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment variables"""
        return SecurityConfig(
            cloud_features_enabled=os.getenv("CLOUD_FEATURES_ENABLED", "true").lower() == "true",
            local_encryption_enabled=os.getenv("LOCAL_ENCRYPTION_ENABLED", "false").lower() == "true",
            telemetry_enabled=os.getenv("TELEMETRY_ENABLED", "false").lower() == "true",
            crash_reporting_enabled=os.getenv("CRASH_REPORTING_ENABLED", "false").lower() == "true"
        )
    
    def _load_google_config(self) -> GoogleCloudConfig:
        """Load Google Cloud configuration from environment variables"""
        return GoogleCloudConfig(
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            project_id=os.getenv("GOOGLE_PROJECT_ID"),
            redirect_uri=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080"),
            scopes=os.getenv("GOOGLE_DRIVE_SCOPES", "https://www.googleapis.com/auth/drive.file")
        )
    
    def get_google_credentials_config(self) -> Optional[Dict[str, Any]]:
        """
        Get Google credentials configuration
        Returns None if credentials are not properly configured
        """
        # First try environment variables
        if all([self.google_config.client_id, 
                self.google_config.client_secret, 
                self.google_config.project_id]):
            return {
                "installed": {
                    "client_id": self.google_config.client_id,
                    "client_secret": self.google_config.client_secret,
                    "project_id": self.google_config.project_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [self.google_config.redirect_uri]
                }
            }
        
        # Fallback to client_secrets.json if it exists
        secrets_file = self.secrets_dir / "client_secrets.json"
        if secrets_file.exists():
            try:
                with open(secrets_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Warning: Could not load client_secrets.json: {e}")
        
        return None
    
    def validate_configuration(self) -> bool:
        """Validate that all required configuration is present"""
        issues: list[str] = []
        
        # Check if cloud features are enabled but not configured
        if self.security_config.cloud_features_enabled:
            google_config = self.get_google_credentials_config()
            if not google_config:
                issues.append("Cloud features enabled but Google credentials not configured")
        
        # Check directory permissions
        for path in [self.app_config.recordings_raw_path, 
                    self.app_config.recordings_edited_path]:
            path_obj = self.project_root / path
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create directory {path}: {e}")
        
        if issues:
            print("❌ Configuration validation failed:")
            for issue in issues:
                print(f"   • {issue}")
            return False
        
        print("✅ Configuration validation successful")
        return True
    
    def create_secure_setup_guide(self) -> str:
        """Create a setup guide for secure configuration"""
        guide = """
# 🔐 Secure Setup Guide for Voice Recorder Pro

## Required for Cloud Features

1. **Create Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing one
   - Enable Google Drive API

2. **Create OAuth Credentials**:
   - Go to APIs & Credentials > Create Credentials > OAuth Client ID
   - Application type: Desktop application
   - Download the JSON file

3. **Configure Environment**:
   Copy .env.template to .env and fill in your values:
   ```bash
   cp .env.template .env
   ```
   
   Edit .env with your credentials:
   ```
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GOOGLE_PROJECT_ID=your_project_id_here
   ```

4. **Secure the Credentials**:
   - NEVER commit .env or client_secrets.json to Git
   - The .gitignore file prevents accidental commits
   - Share credentials securely with team members

## Alternative Setup (File-based)

Place your downloaded OAuth JSON file at:
```
config/client_secrets.json
```

The app will automatically detect and use it.

## Verification

Run the application and check for:
- ✅ "Cloud features initialized" message
- ✅ Google Drive tab appears in the interface
- ✅ OAuth flow works when clicking "Connect to Google Drive"
"""
        return guide

# Global configuration instance
config_manager = ConfigManager()

# Convenience accessors
app_config = config_manager.app_config
security_config = config_manager.security_config
google_config = config_manager.google_config

def get_config() -> ConfigManager:
    """Get the global configuration manager instance"""
    return config_manager
