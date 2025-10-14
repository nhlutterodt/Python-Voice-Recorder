# main.py
# Entry point for Voice Recorder Pro - Enhanced Version with Cloud Integration

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon
from enhanced_editor import EnhancedAudioEditor
from voice_recorder.models.database import engine, Base
from sqlalchemy.sql import text
from assets.icon import get_icon_path, get_app_metadata
import sys
import os

# Cloud integration (optional import)
try:
    from cloud.auth_manager import GoogleAuthManager
    from cloud.feature_gate import FeatureGate
    CLOUD_AVAILABLE = True
    print("☁️ Cloud features available")
except ImportError:
    CLOUD_AVAILABLE = False
    print("ℹ️ Cloud features not available (optional)")
    print("💡 Install cloud dependencies: pip install -r requirements_cloud.txt")

def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def verify_database_setup():
    """Verify database is properly set up before launching application"""
    try:
        # Test database connection
        from voice_recorder.models.database import SessionLocal
        with SessionLocal() as db:
            # Try to query the recordings table to verify it exists
            result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings';"))
            tables = result.fetchall()
            if tables:
                print("✅ Database connectivity verified")
                return True
            else:
                print("❌ Recordings table not found")
                return False
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main application entry point with cloud integration support"""
    print("🚀 Starting Voice Recorder Pro...")
    
    # Initialize database first
    print("📊 Initializing database...")
    if not initialize_database():
        print("❌ Failed to initialize database. Exiting.")
        return 1
    
    # Verify database setup
    if not verify_database_setup():
        print("❌ Database verification failed. Exiting.")
        return 1
    
    # Initialize cloud components if available
    feature_gate = None
    if CLOUD_AVAILABLE:
        try:
            auth_manager = GoogleAuthManager()
            feature_gate = FeatureGate(auth_manager)
            print("✅ Cloud components initialized")
        except Exception as e:
            print(f"⚠️ Cloud initialization failed: {e}")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Get application metadata
    metadata = get_app_metadata()
    
    # Set application properties with enhanced branding
    app.setApplicationName(metadata["name"])
    app.setApplicationVersion(metadata["version"])
    app.setOrganizationName(metadata["organization"])
    app.setOrganizationDomain(metadata["domain"])
    app.setApplicationDisplayName(metadata["name"])
    
    # Set application icon
    icon_path = get_icon_path()
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print(f"✅ Application icon loaded: {icon_path}")
    else:
        print("🎨 Using default system icon (custom icon not found)")
    
    try:
        # Create main window with cloud features if available
        window = EnhancedAudioEditor(feature_gate=feature_gate)
        
        # Set window properties
        window.setWindowTitle(f"{metadata['name']} v{metadata['version']}")
        if icon_path and os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))
        
        window.show()
        
        print("✅ Voice Recorder Pro launched successfully")
        print(f"📱 Application: {metadata['name']} v{metadata['version']}")
        print(f"🏢 Organization: {metadata['organization']}")
        
        if CLOUD_AVAILABLE:
            print("☁️ Cloud features enabled - Sign in for premium features")
        else:
            print("📦 Local features only - Install cloud packages for premium features")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Failed to launch application: {e}")
        QMessageBox.critical(None, "Startup Error", f"Failed to launch Voice Recorder:\n{e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
