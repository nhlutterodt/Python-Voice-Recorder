# 🎤 Voice Recorder Pro - Quick Start Guide

## 🚀 Fastest Way to Launch

**Step 1:** Setup (one-time only)
```powershell
# From repository root
.\Python - Voice Recorder\scripts\setup_local_env.ps1
```

**Step 2:** Launch
```powershell
# Navigate to project directory
cd "Python - Voice Recorder"

# Launch application
.\Launch_VoiceRecorderPro.ps1 -Dev
```

## 🔧 Alternative Launch Methods

### Batch File (Windows)
```batch
cd "Python - Voice Recorder"
.\Launch_VoiceRecorderPro.bat -dev
```

### Manual Launch (for debugging)
```powershell
cd "Python - Voice Recorder"
$env:PYTHONPATH = "."
& "..\venv\Scripts\python.exe" src\enhanced_main.py
```

## ⚠️ Common Issues & Solutions

**Issue:** `ModuleNotFoundError: No module named 'core'`
**Solution:** Make sure you're in the `Python - Voice Recorder` directory and `PYTHONPATH=.`

**Issue:** `python.exe: can't open file`
**Solution:** Use the virtual environment Python: `../venv/Scripts/python.exe`

**Issue:** Virtual environment not found
**Solution:** Run the setup script first: `.\scripts\setup_local_env.ps1`

## 🎯 What Works (Tested Commands)

This command was successfully tested and launches the application:
```cmd
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder" && set PYTHONPATH=. && "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" src\enhanced_main.py
```

## 🔑 Key Success Factors

1. **Working Directory:** Must be `Python - Voice Recorder/`
2. **PYTHONPATH:** Must be set to current directory (`.`)
3. **Python Path:** Must use virtual environment Python
4. **Import Fix:** Changed `from src.waveform_viewer` to `from waveform_viewer`

## 📝 For Developers

When making changes to imports or launch mechanisms, always test with:
- Fresh PowerShell session
- Correct working directory
- Proper PYTHONPATH setting
- Virtual environment activation