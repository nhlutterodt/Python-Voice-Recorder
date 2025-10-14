# Changelog

All notable changes to Voice Recorder Pro will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD pipeline with GitHub Actions
  - Quality gates: mypy, ruff, black, isort, pytest
  - Import validation (canonical imports enforcement)
  - Test coverage reporting (305/308 tests passing - 99%)
  - Artifact generation (junit-report.xml, coverage.xml)
- Backend robustness improvements
  - Database health monitoring and context management
  - Enhanced file storage service with metadata tracking
  - Cloud upload job queue with retry logic
  - Recording service with repository pattern
- Build automation workflow
  - Python wheel and sdist generation
  - Windows executable creation with PyInstaller
- Development tooling
  - Pre-commit hooks configuration
  - Comprehensive test suite (305+ tests)
  - Import checking tool for canonical imports
  - Project metadata in pyproject.toml

### Changed
- Migrated from legacy imports (`import models.*`) to canonical imports (`voice_recorder.*`)
- Reorganized project structure with proper package hierarchy
- Updated README with CI status badges

### Fixed
- Import sorting issues for isort black profile compatibility
- Missing runtime dependencies in CI environment
- System library dependencies for audio and GUI components

### Security
- Added keyring-based credential storage for cloud features
- Implemented OAuth token refresh with locking mechanism

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
