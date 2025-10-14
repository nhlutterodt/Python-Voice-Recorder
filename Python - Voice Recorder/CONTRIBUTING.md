# Contributing to Voice Recorder Pro

Thank you for your interest in contributing to Voice Recorder Pro! This document provides guidelines for contributing to this project.

## 🎯 Project Overview

Voice Recorder Pro is a professional audio recording application developed by Neils Haldane-Lutterodt with GitHub Copilot assistance. The project focuses on providing high-quality audio recording, editing, and cloud integration features.

## 🛠️ Development Setup

### Prerequisites
- Python 3.12 or higher
- Git

### Installation
1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements_dev.txt
   ```

### Pre-commit hooks

We use pre-commit to run linters (ruff/black/isort) and basic checks before committing.

Install and enable hooks in your local environment:

```bash
python -m pip install --upgrade pip
python -m pip install pre-commit
pre-commit install
# To run hooks across the repo once:
pre-commit run --all-files
```

The CI will run the same checks. If you see a failing hook locally, fix the issues and re-run the hooks before pushing.

#### Alternative: install via package extras

If you prefer to use package extras instead of the requirements file you can install the `test` extras exposed in `pyproject.toml`:

```bash
# From the repository root (quotes required on Windows paths that contain spaces):
python -m pip install -e "./Python - Voice Recorder"[test]
# or
pip install -e "./Python - Voice Recorder"[test]
```

Notes:
- `requirements_dev.txt` lists the same runtime and developer tools used in CI (pytest, SQLAlchemy, psutil, ruff, black, isort).
- On Windows, paths with spaces must be quoted as shown above when using PowerShell or CMD.

### Optional: Cloud Features
For cloud integration development:
```bash
pip install -r requirements_cloud.txt
```

## 📋 Development Guidelines

### Code Quality
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Maintain test coverage for new features

### Testing
Run tests before submitting:
```bash
pytest tests/
```

### Building
To build the executable:
```bash
python scripts/build_voice_recorder_pro.py
```

## 🚀 Contribution Process

### 1. Issues
- Check existing issues before creating new ones
- Use clear, descriptive titles
- Provide detailed descriptions with steps to reproduce (for bugs)

### 2. Pull Requests
- Fork the repository and create a feature branch
- Make your changes with clear, atomic commits
- Update documentation if needed
- Ensure all tests pass
- Submit a pull request with a clear description

### 3. Code Review
- All contributions require review
- Address feedback promptly
- Maintain a collaborative, respectful tone

## 🏗️ Project Structure

```
├── audio_processing.py     # Audio processing utilities
├── audio_recorder.py       # Core recording functionality
├── enhanced_editor.py      # Audio editing interface
├── enhanced_main.py        # Main application
├── cloud/                  # Cloud integration modules
├── models/                 # Database models
├── tests/                  # Test suite
├── scripts/                # Build and utility scripts
└── docs/                   # Documentation
```

## 🔧 Feature Areas

### Core Features
- Audio recording and playback
- Real-time waveform visualization
- Audio editing tools
- Performance monitoring

### Cloud Integration
- Google Drive integration
- OAuth authentication
- Cloud storage management

### Build System
- PyInstaller-based executable creation
- Cross-platform compatibility
- Asset management

## 📝 Documentation

- Update README.md for user-facing changes
- Add technical documentation in docs/
- Include docstrings for new functions
- Update this CONTRIBUTING.md if process changes

## 🐛 Bug Reports

Include:
- Operating system and version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs if applicable

## 💡 Feature Requests

- Explain the use case and motivation
- Describe the proposed solution
- Consider backwards compatibility
- Be open to alternative implementations

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🤝 Community

- Be respectful and inclusive
- Help newcomers get started
- Share knowledge and best practices
- Maintain a positive, collaborative environment

## 📧 Contact

For questions about contributing, please open an issue or reach out through the repository's discussion features.

---

*Thank you for helping make Voice Recorder Pro better!*
