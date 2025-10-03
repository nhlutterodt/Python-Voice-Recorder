# Voice Recorder Pro - Troubleshooting Guide

## 🚨 Quick Fix Commands

### Application Won't Start
```cmd
# The command that always works:
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder" && set PYTHONPATH=. && "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" src\enhanced_main.py
```

### Setup Issues
```powershell
# Re-run setup if environment is broken:
.\Python - Voice Recorder\scripts\setup_local_env.ps1
```

## 🔍 Error Diagnosis

### Error: `ModuleNotFoundError: No module named 'src'`
**Cause:** Import path issue in enhanced_editor.py
**Fix:** Check that import is `from waveform_viewer import WaveformViewer` (not `from src.waveform_viewer`)

### Error: `ModuleNotFoundError: No module named 'core'`  
**Cause:** PYTHONPATH not set or wrong working directory
**Fix:** 
1. Ensure working directory is `Python - Voice Recorder/`
2. Set `PYTHONPATH=.`

### Error: `python.exe: can't open file 'enhanced_main.py'`
**Cause:** Wrong working directory
**Fix:** Must be in `Python - Voice Recorder/` directory, not repository root

### Error: `The term '.\Launch_VoiceRecorderPro.ps1' is not recognized`
**Cause:** PowerShell execution policy
**Fix:** Use `powershell -ExecutionPolicy Bypass -File ".\Launch_VoiceRecorderPro.ps1"`

### Error: `UnicodeEncodeError: 'charmap' codec can't encode`
**Status:** Known cosmetic issue - application still works
**Cause:** Emoji characters in log messages
**Impact:** None - app functions normally

## 🛠️ Environment Validation

### Check Virtual Environment
```powershell
Test-Path "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe"
# Should return: True
```

### Check Dependencies
```powershell
& "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" -c "import PySide6, pydub, sounddevice, sqlalchemy; print('✅ All dependencies available')"
```

### Check Project Structure
```powershell
Get-ChildItem "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src\enhanced_main.py"
# Should show the file exists
```

## 🚀 Launch Method Decision Tree

```
Start Here: Need to launch Voice Recorder Pro
│
├── Fresh setup needed? → YES: Run setup_local_env.ps1 → Continue
├── NO: Continue
│
├── Quick launch? → YES: Use Launch_VoiceRecorderPro.bat -dev
├── NO: Continue  
│
├── Debugging needed? → YES: Use direct cmd command
├── NO: Use batch file
│
└── Still failing? → Check error patterns above
```

## 📋 Pre-Launch Checklist

- [ ] Virtual environment exists at correct path
- [ ] Python executable works: `python.exe -c "print('test')"`
- [ ] Dependencies installed: Can import PySide6, pydub, sounddevice
- [ ] Project files exist: enhanced_main.py found
- [ ] Working directory correct: Must be `Python - Voice Recorder/`
- [ ] PYTHONPATH set: Must be `.` (current directory)

## 🔧 Recovery Procedures

### Complete Environment Reset
```powershell
# 1. Delete virtual environment
Remove-Item "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv" -Recurse -Force

# 2. Re-run setup
.\Python - Voice Recorder\scripts\setup_local_env.ps1

# 3. Test launch
.\Python - Voice Recorder\Launch_VoiceRecorderPro.bat -dev
```

### Import Path Fix
If you see `from src.module` imports, change them to `from module`:
```python
# Wrong:
from src.waveform_viewer import WaveformViewer

# Correct:
from waveform_viewer import WaveformViewer
```

## 📞 Support Information

**Working Configuration (Tested):**
- OS: Windows 10/11
- Python: 3.12 (from virtual environment)
- Working Directory: `Python - Voice Recorder/`
- PYTHONPATH: `.`
- Launch Method: Batch file or direct cmd

**Known Issues:**
- Unicode encoding warnings (cosmetic only)
- PowerShell working directory management
- Execution policy restrictions

**Verified Working Commands:**
1. `.\Launch_VoiceRecorderPro.bat -dev`
2. Direct cmd execution with full paths
3. Manual launch with proper environment setup