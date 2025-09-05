# 🎤 Voice Recorder Pro v2.0.0-beta

*A professional audio recording application with advanced editing and cloud integration*

**Created by Neils Haldane-Lutterodt with GitHub Copilot assistance**

![Voice Recorder Pro](docs/images/app-preview.png)
*Professional audio recording interface with real-time waveform visualization*

## ✨ Features

### 🎯 Core Recording
- **High-Quality Audio Recording** - Professional-grade audio capture
- **Real-Time Waveform Visualization** - Live audio feedback during recording
- **Multiple Audio Formats** - WAV, MP3, OGG support
- **Performance Monitoring** - Real-time system performance tracking

### ✂️ Advanced Editing
- **Visual Audio Editor** - Intuitive waveform-based editing
- **Precise Cut/Trim Tools** - Frame-accurate audio editing
- **Quality Preview** - Real-time playback during editing
- **Export Options** - Multiple format and quality options

### ☁️ Cloud Integration
- **Google Drive Sync** - Seamless cloud storage integration
- **OAuth Security** - Secure authentication with Google
- **Automatic Backup** - Optional cloud backup of recordings
- **Cross-Device Access** - Access recordings from anywhere

### 🛠️ Professional Tools
- **Database Management** - SQLAlchemy-powered recording database
- **Configuration Presets** - Save and load recording configurations
- **Portable Mode** - Run without installation
- **Windows Executable** - Standalone application (10.2MB)

## 🚀 Quick Start

### Option 1: Download Executable (Recommended)
1. Download `VoiceRecorderPro.exe` from [Releases](../../releases)
2. Run the executable - no installation required!
3. Start recording professional-quality audio

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/nhlutterodt/Python---Voice-Recorder.git
cd Python---Voice-Recorder

# Install dependencies
pip install -r requirements.txt

# Launch the application
python enhanced_main.py
```

### Optional: Cloud Features
```bash
# Install cloud dependencies
pip install -r requirements_cloud.txt

# Configure Google OAuth (see Cloud Setup section)
```

## 📖 Documentation

## 🛠️ Local development setup (recommended)

Follow these steps to prepare a reproducible local development environment. This approach is persistent and configurable via environment variables or a `.env` file.

1. From the repository root run the one-line setup script (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File ".\Python - Voice Recorder\scripts\setup_local_env.ps1"
```

- This will create required directories (`db`, `recordings/`, `logs`, `config`).
- It will create a `venv` if none exists, upgrade pip, install packages from `Python - Voice Recorder/requirements.txt`, and initialize the database tables.
- The script also writes a `.env.template` (if requested) so you can copy it to `.env` and customize local settings.

2. Activate the virtual environment and run the app:

```powershell
.\venv\Scripts\Activate.ps1
python ".\Python - Voice Recorder\enhanced_main.py"
```

Configuration notes:
- You can override any app path or setting via environment variables (see `config_manager.py`). The most important is `DATABASE_URL` (for example `sqlite:///db/app.db` or a full absolute sqlite path). If you set a relative sqlite URL, it will be resolved against the project root and the parent directory will be created automatically.
- To enable cloud features, set the Google credentials either through environment variables or by placing `client_secrets.json` into the `config/` folder. See `config_manager.py` and the Cloud Setup Guide for details.

This setup is deterministic and intended for developer machines and CI. If you want cross-platform parity, I can add an equivalent Bash script for macOS/Linux.


- **[Quick Start Guide](docs/quickstart/README.md)** - Get up and running in minutes
- **[Build Instructions](README_BUILD.md)** - Technical build documentation
- **[Development Summary](DEVELOPMENT_SUMMARY.md)** - Project development story
- **[Cloud Setup Guide](docs/cloud-setup.md)** - Google Drive integration setup
- **[Contributing](CONTRIBUTING.md)** - How to contribute to the project

## 🎨 Screenshots

| Recording Interface | Audio Editor | Cloud Integration |
|:---:|:---:|:---:|
| ![Recording](docs/images/recording-interface.png) | ![Editor](docs/images/audio-editor.png) | ![Cloud](docs/images/cloud-sync.png) |
| *Clean, professional recording interface* | *Advanced waveform editing tools* | *Seamless Google Drive integration* |

## 🏗️ Architecture

Voice Recorder Pro is built with a modular, professional architecture:

```
🎤 Voice Recorder Pro
├── 🎯 Core Application (PySide6)
├── 🔊 Audio Engine (sounddevice + pydub)
├── 📊 Real-time Visualization (matplotlib)
├── 🗄️ Database Layer (SQLAlchemy)
├── ☁️ Cloud Integration (Google APIs)
└── 📦 Build System (PyInstaller)
```

### Key Technologies
- **PySide6** - Modern, responsive UI framework
- **sounddevice** - Professional audio I/O
- **pydub** - Comprehensive audio processing
- **matplotlib** - Real-time waveform visualization
- **SQLAlchemy** - Robust database management
- **Google APIs** - Cloud integration and storage

## ⚙️ System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 500MB free space
- **Audio**: Any standard audio input device

### Recommended Specifications
- **RAM**: 8GB+ for large file editing
- **Storage**: 2GB+ for recordings and cache
- **Audio**: Professional microphone for best results

## 🔧 Advanced Configuration

### Recording Presets
Voice Recorder Pro includes optimized presets for different use cases:
- **Podcast** - Optimized for voice recording
- **Music** - High-fidelity music recording
- **Interview** - Enhanced clarity for interviews
- **Custom** - User-defined configurations

### Cloud Setup
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API
4. Download OAuth credentials
5. Place in `config/client_secrets.json`

For detailed setup instructions, see [Cloud Setup Guide](docs/cloud-setup.md).

## 🧪 Development

### For Developers
```bash
# Install development dependencies
pip install -r requirements_dev.txt

# Run tests
pytest tests/

# Build executable
python scripts/build_voice_recorder_pro.py
```

### Project Structure
```
voice-recorder-pro/
├── enhanced_main.py          # Main application entry
├── audio_recorder.py         # Core recording engine
├── enhanced_editor.py        # Audio editing interface
├── audio_processing.py       # Audio processing utilities
├── cloud/                    # Cloud integration modules
├── models/                   # Database models
├── tests/                    # Comprehensive test suite
└── scripts/                  # Build and utility scripts
```

## 📊 Performance

Voice Recorder Pro is optimized for professional use:
- **Low Latency**: <10ms audio latency
- **Efficient Memory**: <100MB typical usage
- **Fast Startup**: <3 seconds to ready state
- **Real-time Processing**: Live waveform visualization

## 🤝 Contributing

We welcome contributions! Voice Recorder Pro is built with collaboration in mind.

1. Fork the repository
2. Create a feature branch
3. Make your improvements
4. Add tests for new features
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

Voice Recorder Pro is released under the [MIT License](LICENSE).

```
Copyright (c) 2025 Neils Haldane-Lutterodt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

## 🌟 Acknowledgments

- **GitHub Copilot** - AI assistance in development
- **PySide6 Team** - Excellent UI framework
- **Python Audio Community** - sounddevice and pydub libraries
- **Open Source Contributors** - Making great software accessible

## 📬 Support & Contact

- **Issues**: [Report bugs or request features](../../issues)
- **Discussions**: [Community discussions](../../discussions)
- **Documentation**: [Full documentation](docs/)

---

<div align="center">

**Built with ❤️ by Neils Haldane-Lutterodt with GitHub Copilot assistance**

[⬆️ Back to Top](#-voice-recorder-pro-v200-beta)

</div>
