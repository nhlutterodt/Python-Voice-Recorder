# Release Checklist

This document outlines the steps required to prepare and publish a new release of Voice Recorder Pro.

## Pre-Release Preparation

### 1. Version Bump
- [ ] Update version number in `pyproject.toml` (follow [Semantic Versioning](https://semver.org/))
- [ ] Update version in `src/entrypoint.py` (if applicable)
- [ ] Update any hardcoded version references in documentation

### 2. Documentation Updates
- [ ] Update `CHANGELOG.md` with all changes since last release
  - Move items from `[Unreleased]` to new version section
  - Add release date
  - Follow format: `## [X.Y.Z] - YYYY-MM-DD`
- [ ] Review and update `README.md` if needed
- [ ] Update `QUICKSTART.md` with any new features or changes
- [ ] Check that all documentation is accurate and up-to-date

### 3. Code Quality Checks
- [ ] Run full test suite locally: `pytest`
- [ ] Verify all tests pass (target: 99%+ pass rate)
- [ ] Run linting checks: `ruff check .`
- [ ] Run formatting checks: `black --check .`
- [ ] Run import sorting check: `isort --check-only .`
- [ ] Run type checking: `mypy src`
- [ ] Check for legacy imports: `python tools/check_imports.py "Python - Voice Recorder"`
- [ ] Review code coverage report

### 4. CI/CD Verification
- [ ] Ensure all CI checks pass on main branch
- [ ] Verify CI workflow run: `gh run list --branch main --limit 1`
- [ ] Check CI status: All quality gates must be green
  - mypy (type checking)
  - check_imports (canonical imports)
  - ruff (linting)
  - black (formatting)
  - isort (import sorting)
  - pytest (unit tests)
- [ ] Review test results: Minimum 99% pass rate required
- [ ] Verify artifacts are generated correctly
  - junit-report.xml
  - coverage.xml

## Build Process

### 5. Build Artifacts
- [ ] Trigger build workflow manually or via tag push
- [ ] Verify build workflow completes successfully
- [ ] Download and test artifacts:
  - [ ] Python wheel (`.whl`)
  - [ ] Source distribution (`.tar.gz`)
  - [ ] Windows executable (`.exe`) - if applicable

### 6. Local Build Verification
- [ ] Build wheel locally: `python -m build`
- [ ] Install wheel in clean environment: `pip install dist/voice_recorder_pro-X.Y.Z-py3-none-any.whl`
- [ ] Run smoke tests in clean environment
- [ ] Test Windows executable (if built):
  - [ ] Launch application
  - [ ] Test basic recording functionality
  - [ ] Test audio playback
  - [ ] Test cloud upload (if credentials configured)

## Release Creation

### 7. Git Operations
- [ ] Create release branch: `git checkout -b release/vX.Y.Z`
- [ ] Commit version bump and changelog updates
- [ ] Push release branch: `git push origin release/vX.Y.Z`
- [ ] Create PR to main and get approval
- [ ] Merge PR to main
- [ ] Pull latest main: `git checkout main && git pull`
- [ ] Create and push tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin vX.Y.Z`

### 8. GitHub Release
- [ ] Navigate to repository releases page
- [ ] Click "Draft a new release"
- [ ] Select tag: `vX.Y.Z`
- [ ] Release title: `Voice Recorder Pro vX.Y.Z`
- [ ] Copy relevant section from CHANGELOG.md to release notes
- [ ] Attach build artifacts:
  - [ ] wheel file
  - [ ] sdist file
  - [ ] Windows executable (if applicable)
  - [ ] junit-report.xml (optional)
  - [ ] coverage.xml (optional)
- [ ] Mark as pre-release if beta/alpha
- [ ] Publish release

### 9. Post-Release Verification
- [ ] Verify release is visible on GitHub
- [ ] Test installation from GitHub release:
  - [ ] Download wheel from release
  - [ ] Install in clean environment
  - [ ] Run application
- [ ] Verify download links work
- [ ] Check release artifacts integrity

## Post-Release Tasks

### 10. Communication
- [ ] Announce release (if applicable)
  - Internal team notification
  - User documentation update
  - Release notes distribution
- [ ] Update project board/issues
  - Close completed milestone
  - Create next milestone
  - Update issue labels

### 11. Monitoring
- [ ] Monitor for bug reports
- [ ] Check CI/CD pipeline remains green
- [ ] Review usage metrics (if telemetry enabled)
- [ ] Prepare hotfix process if needed

### 12. Cleanup
- [ ] Delete release branch (if merged)
- [ ] Archive old builds (keep last 3 releases)
- [ ] Update issue tracker with "released" label
- [ ] Begin next development cycle
  - [ ] Create `[Unreleased]` section in CHANGELOG.md
  - [ ] Plan next version features

---

## Quick Release Command Reference

```bash
# Check CI status
gh run list --branch main --limit 1
gh run view <run-id>

# Create release branch
git checkout -b release/vX.Y.Z

# Tag release
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z

# Build locally
cd "Python - Voice Recorder"
python -m build

# Run full quality checks
pytest
ruff check .
black --check .
isort --check-only .
mypy src
python tools/check_imports.py "Python - Voice Recorder"
```

---

## Rollback Procedure

If issues are discovered post-release:

1. **Immediate Actions**
   - [ ] Mark release as "pre-release" or hide it
   - [ ] Add warning to release notes
   - [ ] Document known issues

2. **Hotfix Process**
   - [ ] Create hotfix branch: `git checkout -b hotfix/vX.Y.Z+1`
   - [ ] Apply fixes
   - [ ] Follow abbreviated release checklist
   - [ ] Release hotfix version

3. **Rollback Release** (last resort)
   - [ ] Delete GitHub release
   - [ ] Delete git tag: `git push --delete origin vX.Y.Z`
   - [ ] Communicate rollback to users

---

## Notes

- **Semantic Versioning Guidelines:**
  - MAJOR version: Incompatible API changes
  - MINOR version: Backwards-compatible new features
  - PATCH version: Backwards-compatible bug fixes
  
- **Pre-release versions:**
  - Alpha: `vX.Y.Z-alpha.N`
  - Beta: `vX.Y.Z-beta.N`
  - Release Candidate: `vX.Y.Z-rc.N`

- **Minimum Requirements for Release:**
  - All CI checks passing
  - 99%+ test pass rate
  - No critical bugs
  - Documentation updated
  - Changelog complete
