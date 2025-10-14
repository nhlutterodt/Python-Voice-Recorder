# Clean Release Creator - Usage Guide

## Overview
The `create_clean_release.ps1` script automatically creates a production-ready copy of Voice Recorder Pro by intelligently filtering out development artifacts and organizing files for public release.

## Quick Usage

### Basic Usage
```powershell
# Create clean release in default location
.\scripts\create_clean_release.ps1

# Create in custom location
.\scripts\create_clean_release.ps1 -DestinationPath "d:\my-clean-project"

# Dry run to see what would be copied
.\scripts\create_clean_release.ps1 -DryRun -Verbose

# Force overwrite existing destination
.\scripts\create_clean_release.ps1 -Force
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-DestinationPath` | Where to create the clean copy | `d:\voice-recorder-pro-public` |
| `-Force` | Overwrite existing destination | `false` |
| `-DryRun` | Show what would be copied without actually copying | `false` |
| `-Verbose` | Show detailed file operations | `false` |

## What Gets Included

### ✅ Core Application Files
- `src/entrypoint.py` - Main application entry (module)
- `audio_recorder.py` - Core recording engine
- `enhanced_editor.py` - UI components
- `audio_processing.py` - Audio utilities
- `config_manager.py` - Configuration management
- `performance_monitor.py` - Performance tools
- `version.py` - Version information

### ✅ Essential Configuration
- `requirements*.txt` - All dependency files
- `.gitignore` - Clean production gitignore
- `.env.template` - Configuration template
- `LICENSE` - MIT license
- `VoiceRecorderPro.spec` - Build configuration

### ✅ Documentation (Clean)
- `README.md` - Professional project overview
- `CONTRIBUTING.md` - Community guidelines
- `docs/` - Essential documentation only (no archives)

### ✅ Core Modules
- `cloud/` - Cloud integration (Python files only)
- `models/` - Database models
- `src/` - Source modules
- `assets/` - Application assets
- `config/` - Configuration templates (excludes secrets)

### ✅ Build System
- `scripts/` - Essential build scripts only
- `tests/` - Clean test suite

## What Gets Excluded

### ❌ Development Artifacts
- All files with `ASSESSMENT`, `SUMMARY`, `PLAN` in the name
- `docs/archive/` - Complete development history
- `docs/assessments/` - Project assessments
- `docs/development/` - Development logs
- `READY_FOR_RELEASE.md` - Release preparation docs
- `blog_post_draft.md` - Personal blog content

### ❌ Runtime/Build Artifacts
- `recordings/` - Personal recordings
- `db/` - Database files
- `__pycache__/` - Python cache
- `.pytest_cache/` - Test cache
- `.benchmarks/` - Performance benchmarks
- `build_info.json` - Build artifacts

### ❌ Personal/Development Files
- `launch*.bat` - Personal launch scripts
- `launch*.ps1` - Personal launch scripts
- `.vscode/` - Editor settings
- Demo and test scripts

## Example Workflow

```powershell
# Step 1: Preview what will be copied
.\scripts\create_clean_release.ps1 -DryRun -Verbose

# Step 2: Create the clean copy
.\scripts\create_clean_release.ps1 -DestinationPath "d:\voice-recorder-pro-clean"

# Step 3: Navigate to clean copy
cd "d:\voice-recorder-pro-clean"

# Step 4: Initialize new git repository
git init
git add .
git commit -m "Initial commit - Voice Recorder Pro v2.0.0-beta"

# Step 5: Create GitHub repository and push
git remote add origin https://github.com/yourusername/voice-recorder-pro.git
git branch -M main
git push -u origin main
```

## Output Structure

The script creates this clean structure:
```
voice-recorder-pro-public/
├── README.md                    # Professional overview
├── CONTRIBUTING.md              # Community guidelines
├── LICENSE                      # MIT license
├── requirements.txt             # Dependencies
├── .gitignore                   # Production gitignore
├── src/entrypoint.py            # Application entry (module)
├── [core application files]     # All essential Python files
├── cloud/                       # Cloud integration
├── models/                      # Database models
├── assets/                      # Application assets
├── config/                      # Configuration templates
├── scripts/                     # Essential build scripts
├── tests/                       # Clean test suite
└── docs/                        # Essential documentation
    ├── README.md                # Documentation hub
    ├── quickstart/              # Getting started
    ├── setup/                   # Installation guides
    ├── api/                     # Technical docs
    └── images/                  # Screenshots (empty)
```

## Post-Creation Steps

1. **Review the structure** - Check that everything looks correct
2. **Add screenshots** - Place app images in `docs/images/`
3. **Test the build** - Ensure the application still builds correctly
4. **Create GitHub repo** - Initialize as new public repository
5. **Create release** - Package the executable for download

## Troubleshooting

### Permission Errors
```powershell
# Run as administrator if you get permission errors
Start-Process PowerShell -Verb RunAs
```

### Execution Policy
```powershell
# Enable script execution if needed
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Path Issues
- Ensure you're running from the project root directory
- Use absolute paths if relative paths cause issues
- Check that source files exist before running

This script provides a professional, automated way to create clean releases suitable for public GitHub repositories!
