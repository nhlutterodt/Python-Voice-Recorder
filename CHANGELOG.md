# Changelog

All notable changes to Voice Recorder Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2025-10-15

### Added
- Complete CI/CD pipeline with GitHub Actions
  - Automated testing with pytest (305/308 tests passing - 99%)
  - Quality gates: mypy, ruff, black, isort
  - Import validation (canonical imports enforcement)
  - Test coverage and JUnit reporting
  - Security scanning with pip-audit
- Build automation workflow
  - Python wheel and source distribution generation
  - Windows executable creation with PyInstaller
  - Pre-built PyAudio wheels for Windows
  - Artifact retention (30 days)
- Release automation workflow
  - Tag-triggered GitHub Releases
  - Automatic changelog extraction
  - Draft release creation with artifacts
  - Smoke test validation
- Development tooling
  - Pre-commit hooks for code quality
  - Comprehensive documentation (CONTRIBUTING.md, RELEASE_CHECKLIST.md)
  - CI/CD roadmap tracking (18/23 tasks complete)
  - Import checking tool for canonical imports

### Changed
- Standardized code formatting with black and isort
- Enforced canonical imports (voice_recorder.* instead of models.*)
- Organized dev dependencies in requirements_dev.txt
- Improved Windows build process with pre-built wheels
- Enhanced test suite with environment-specific xfail markers

### Fixed
- Windows executable build PyAudio dependency issues
- Release workflow artifact upload (package name and dynamic detection)
- Legacy import patterns (0 remaining)
- Test suite environment compatibility (CI vs local)
- Import sorting for isort black profile compatibility

### Security
- Added pip-audit for automated vulnerability scanning
- Non-blocking security reports in CI
- Keyring-based credential storage for cloud features
- OAuth token refresh with locking mechanism

## [2.0.0-beta] - 2024-10-01

### Added
- Initial release with voice recording capabilities
- Audio editing features
- Cloud backup functionality
- Performance monitoring

---

## Release Types

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
