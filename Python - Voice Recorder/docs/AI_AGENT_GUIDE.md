# AI Agent Memory Guide - Voice Recorder Pro

**For AI Coding Agents: How to Successfully Launch and Work with Voice Recorder Pro**

## 🎯 Critical Success Pattern (MEMORIZE THIS)

### The Working Command Pattern
```cmd
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder" && set PYTHONPATH=. && "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" -m src.entrypoint
```

This command ALWAYS works because:
1. **Absolute paths** - No working directory confusion
2. **cmd execution** - Avoids PowerShell working directory issues  
3. **PYTHONPATH=.** - Resolves module import issues
4. **Virtual environment Python** - Uses correct Python with dependencies

### Why Other Approaches Fail

❌ **PowerShell virtual environment activation**
- Reason: Changes working directory unpredictably
- Symptom: `python.exe: can't open file` errors

❌ **Relative import paths (from src.module)**  
- Reason: Python can't find src module
- Symptom: `ModuleNotFoundError: No module named 'src'`

❌ **System Python instead of venv Python**
- Reason: Missing dependencies
- Symptom: `ModuleNotFoundError` for PySide6, pydub, etc.

❌ **Wrong working directory**
- Reason: Relative paths in imports break
- Symptom: `ModuleNotFoundError: No module named 'core'`

## 🔧 Reliable Launch Methods (In Order of Preference)

### Method 1: Batch File (Recommended)
```bash
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder"
.\Launch_VoiceRecorderPro.bat -dev
```
✅ Handles all path management automatically

### Method 2: Direct Command (For Debugging)
```cmd
cmd /c 'cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder" && set PYTHONPATH=. && "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" -m src.entrypoint'
```
✅ Always works, full control

### Method 3: PowerShell (Advanced)
```powershell
# Must bypass execution policy and set paths carefully
powershell -ExecutionPolicy Bypass -Command "cd 'C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder'; `$env:PYTHONPATH='.'; & 'C:\Users\Owner\Voice-Recorder\Python-Voice-Recorder\venv\Scripts\python.exe' -m src.entrypoint"
```

## 🚨 Common Pitfalls for AI Agents

### 1. Working Directory Confusion
**Problem:** PowerShell `cd` commands don't persist between tool calls
**Solution:** Use absolute paths or cmd with && chaining

### 2. Virtual Environment Activation Issues  
**Problem:** `.\venv\Scripts\Activate.ps1` changes working directory
**Solution:** Use direct path to `python.exe` instead of activation

### 3. Module Import Errors
**Problem:** Python can't find project modules
**Root Cause:** PYTHONPATH not set or wrong working directory
**Solution:** Always set `PYTHONPATH=.` from project root

### 4. Execution Policy Blocks
**Problem:** PowerShell won't run .ps1 scripts
**Solution:** Use `powershell -ExecutionPolicy Bypass` or batch files

## 🧠 AI Agent Decision Tree

```
Need to launch Voice Recorder Pro?
├── First time setup needed?
│   ├── YES → Run: .\Python - Voice Recorder\scripts\setup_local_env.ps1
│   └── NO → Continue to launch
├── User wants quick launch?
│   ├── YES → Use: .\Launch_VoiceRecorderPro.bat -dev
│   └── NO → Continue to manual
├── Need debugging/development?
│   ├── YES → Use direct cmd command (Method 2)
│   └── NO → Use batch file
└── Having import errors?
    ├── ModuleNotFoundError: src → Check PYTHONPATH=.
    ├── ModuleNotFoundError: core → Check working directory
    └── Missing dependencies → Check virtual environment
```

## 📁 File Structure Memory Aid

```
Python-Voice-Recorder/                    # Git repository root
├── venv/                                 # Virtual environment
│   └── Scripts/python.exe               # The Python to use
├── Python - Voice Recorder/             # Project root (note the space!)
│   ├── src/
│   │   ├── entrypoint.py               # Main entry point (use `python -m src.entrypoint`)
│   │   ├── enhanced_editor.py          # Main UI
│   │   └── config_manager.py           # Configuration
│   ├── core/                           # Core modules
│   ├── models/                         # Database models  
│   ├── cloud/                          # Cloud integration
│   ├── Launch_VoiceRecorderPro.bat     # Reliable launcher
│   ├── Launch_VoiceRecorderPro.ps1     # PowerShell launcher
│   └── scripts/
│       └── setup_local_env.ps1         # One-time setup
```

## 🔍 Debugging Checklist for AI Agents

When launch fails, check in this order:

1. **Virtual environment exists?**
   ```bash
   Test-Path "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe"
   ```

2. **Working directory is project root?**
   ```bash
   Get-Location
   # Should be: C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder
   ```

3. **PYTHONPATH is set?**
   ```bash
   echo $env:PYTHONPATH
   # Should be: . (current directory)
   ```

4. **Dependencies installed?**
   ```bash
   & "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" -c "import PySide6; print('Dependencies OK')"
   ```

## 🎯 AI Agent Success Metrics

✅ **Successful Launch Indicators:**
- See: "Starting Enhanced Voice Recorder application"
- See: "Application event loop starting"  
- See: "Main window created and displayed"
- Application window appears

❌ **Failure Indicators:**
- `ModuleNotFoundError` → Path/import issue
- `can't open file` → Working directory issue
- `not recognized as...` → Script not found/execution policy
- `UnicodeEncodeError` → Known cosmetic issue (app still works)

## 💡 Pro Tips for AI Agents

1. **Always use the batch file first** - It handles complexity for you
2. **When debugging, use absolute paths** - Eliminates variables
3. **cmd is more reliable than PowerShell** - For this project
4. **The space in "Python - Voice Recorder"** - Always quote the path
5. **Unicode errors are cosmetic** - App works despite logging errors

## 📚 Context for AI Agents

This project has a complex launch setup because:
- **PySide6 GUI application** - Requires proper Qt environment
- **Mixed import styles** - Some absolute, some relative
- **Virtual environment required** - Many dependencies
- **Windows path complexity** - Spaces in directory names
- **PowerShell quirks** - Working directory management issues

The launch scripts we created solve these problems systematically.