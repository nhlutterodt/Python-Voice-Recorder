# Voice Recorder Pro - Development Workflow

## 🚀 Getting Started (New Developers)

### Initial Setup
```powershell
# 1. Clone repository
git clone https://github.com/nhlutterodt/Python-Voice-Recorder.git
cd Python-Voice-Recorder

# 2. Run setup script  
.\Python - Voice Recorder\scripts\setup_local_env.ps1

# 3. Launch application
cd "Python - Voice Recorder"
.\Launch_VoiceRecorderPro.bat -dev
```

## 🔄 Daily Development Workflow

### Starting Development Session
```bash
# Navigate to project
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder"

# Launch app for testing
.\Launch_VoiceRecorderPro.bat -dev
```

### Making Code Changes
1. **Edit files** in `src/`, `models/`, `core/`, etc.
2. **Test changes** by relaunching the app
3. **No restart needed** for most Python changes (restart for import changes)

### Testing Changes
```powershell
# Quick launch for testing
.\Launch_VoiceRecorderPro.bat -dev

# Or manual launch for debugging
$env:PYTHONPATH = "."
& "..\venv\Scripts\python.exe" src\enhanced_main.py
```

## 🏗️ Architecture Overview

### Key Components
- **`src/enhanced_main.py`** - Application entry point
- **`src/enhanced_editor.py`** - Main UI and editor logic
- **`src/audio_recorder.py`** - Recording functionality  
- **`src/config_manager.py`** - Configuration management
- **`core/`** - Core utilities (logging, database)
- **`models/`** - Database models
- **`cloud/`** - Cloud integration features

### Data Flow
```
User Input → Enhanced Editor → Audio Recorder → File System
     ↓              ↓              ↓            ↓
UI Updates ←  Database ←    Audio Processing ← Storage
```

## 🔧 Common Development Tasks

### Adding New Features
1. **Identify component** - Which module should contain the feature?
2. **Update UI** - Modify `enhanced_editor.py` if UI changes needed
3. **Add business logic** - Create/modify appropriate service modules
4. **Update database** - Add models or migrations if data storage needed
5. **Test thoroughly** - Use launch scripts to verify changes

### Database Changes
```powershell
# Create migration
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "Description"

# Apply migration  
.\venv\Scripts\python.exe -m alembic upgrade head
```

### Adding Dependencies
```powershell
# Install new package
.\venv\Scripts\python.exe -m pip install package-name

# Update requirements
.\venv\Scripts\python.exe -m pip freeze > requirements.txt
```

## 🧪 Testing

### Manual Testing
```powershell
# Launch app and test features
.\Launch_VoiceRecorderPro.bat -dev

# Test specific components
.\venv\Scripts\python.exe -c "from src.audio_recorder import AudioRecorderManager; print('Import OK')"
```

### Automated Testing
```powershell
# Run tests (if available)
.\venv\Scripts\python.exe -m pytest tests/
```

## 📦 Building

### Development Build
```powershell
# Test build process
python scripts\build_voice_recorder_pro.py
```

### Production Build
```powershell
# Create distributable executable
python scripts\build_exe.py
```

## 🐛 Debugging

### Debug Mode Launch
```powershell
# Launch with debug output
$env:LOG_LEVEL = "DEBUG"  
.\Launch_VoiceRecorderPro.bat -dev
```

### Common Debug Scenarios
- **Import errors** → Check PYTHONPATH and working directory
- **Audio issues** → Check sounddevice installation and permissions
- **Database errors** → Check SQLite file permissions and schema
- **UI issues** → Check PySide6 installation and Qt dependencies

## 📋 Code Quality

### Before Committing
- [ ] App launches successfully
- [ ] No import errors  
- [ ] Core features work (record, play, edit)
- [ ] No obvious UI errors
- [ ] Database operations work

### Code Style
- Follow existing patterns in the codebase
- Use type hints where possible
- Add docstrings for new functions
- Handle exceptions appropriately

## 🔄 Git Workflow

### Feature Development
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
# ... development work ...

# Commit changes
git add .
git commit -m "Add feature: description"

# Push and create PR
git push origin feature/your-feature-name
```

### Deployment
- Features merge to `main` branch
- CI/CD builds and tests automatically
- Releases created from `main` branch

## 💡 Tips for Success

1. **Always test the launch** - Use the batch file to verify changes
2. **Use absolute paths** - Avoid working directory issues
3. **Check imports carefully** - Module path issues are common
4. **Virtual environment is key** - Always use the project venv
5. **Database is SQLite** - File-based, easy to reset if needed
6. **Cloud features optional** - App works without Google APIs
7. **Error logs are helpful** - Check console output for clues

## 🆘 Getting Help

### Resources
- **AI_AGENT_GUIDE.md** - For AI assistance patterns
- **TROUBLESHOOTING.md** - Common error solutions  
- **README.md** - User-facing documentation
- **`.github/copilot-instructions.md`** - AI coding guidance

### Emergency Recovery
```powershell
# Nuclear option: complete reset
Remove-Item "venv" -Recurse -Force
.\Python - Voice Recorder\scripts\setup_local_env.ps1
```