# Medium-Term Tasks Implementation Plan (Tasks #19-20)

**Date**: October 16, 2025  
**Phase**: Medium-term (Post v2.1.0)  
**Status**: Planning

---

## Overview

After successfully completing Phase 1 (Tasks #1-18) and releasing v2.1.0, we're now ready to tackle medium-term improvements focused on:
- **Task #19**: Release automation improvements
- **Task #20**: Telemetry/observability hooks

---

## Task #19: Release Automation Improvements

### Current State Analysis

**What We Have**:
- ✅ Manual release workflow (`.github/workflows/release.yml`)
- ✅ Tag-triggered releases
- ✅ Changelog extraction from `CHANGELOG.md`
- ✅ Artifact building and uploading
- ✅ Draft release creation

**What's Manual**:
- ❌ Changelog updates (manual editing)
- ❌ Version bumping in `pyproject.toml`
- ❌ Tag creation and push
- ❌ Commit message standardization
- ❌ Release notes generation

### Goals

1. **Automated Version Management**
   - Determine next version based on commit messages
   - Update `pyproject.toml` automatically
   - Follow semantic versioning rules

2. **Automated Changelog Generation**
   - Generate changelog from commit messages
   - Categorize changes (feat, fix, chore, etc.)
   - Maintain `CHANGELOG.md` format

3. **Streamlined Release Process**
   - Reduce manual steps
   - Enforce commit message conventions
   - Auto-create tags and releases

### Implementation Options

#### Option A: Python Semantic Release (RECOMMENDED)
**Pros**:
- ✅ Python-native solution
- ✅ Well-maintained and active
- ✅ Conventional commits support
- ✅ GitHub Actions integration
- ✅ Changelog generation included
- ✅ Version bumping built-in

**Cons**:
- Requires learning configuration
- Adds dependency to dev tools

**Implementation**:
```yaml
# .github/workflows/release.yml (new approach)
- uses: python-semantic-release/python-semantic-release@v8
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

#### Option B: Semantic Release (Node.js)
**Pros**:
- ✅ Industry standard
- ✅ Extensive plugin ecosystem
- ✅ Mature and battle-tested

**Cons**:
- ❌ Requires Node.js in workflow
- ❌ Not Python-native
- ❌ More complex configuration

#### Option C: Custom Scripts
**Pros**:
- ✅ Full control
- ✅ No external dependencies
- ✅ Tailored to our needs

**Cons**:
- ❌ More maintenance
- ❌ Reinventing the wheel
- ❌ Less battle-tested

### Recommended Approach: Option A (Python Semantic Release)

**Estimated Effort**: 3 days
- Day 1: Setup and configuration
- Day 2: Testing and refinement
- Day 3: Documentation and rollout

**Steps**:

1. **Install and Configure** (4 hours)
   - Add `python-semantic-release` to `requirements_dev.txt`
   - Configure in `pyproject.toml`
   - Set up commit message parser (conventional commits)

2. **Update Workflows** (3 hours)
   - Modify release workflow to use PSR
   - Add commit lint checks to CI
   - Update pre-commit hooks

3. **Document Process** (2 hours)
   - Update `CONTRIBUTING.md` with commit conventions
   - Update `RELEASE_CHECKLIST.md`
   - Create examples and templates

4. **Test Release Process** (2 hours)
   - Create test branch
   - Simulate release with test commits
   - Verify changelog generation

5. **Rollout** (1 hour)
   - Merge to main
   - Document for team
   - Create announcement

### Conventional Commits Standard

We'll adopt [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature (triggers MINOR bump)
- `fix`: Bug fix (triggers PATCH bump)
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test additions/changes
- `chore`: Build/tooling changes
- `ci`: CI/CD changes
- `BREAKING CHANGE`: (triggers MAJOR bump)

**Examples**:
```bash
feat: add recording pause functionality
fix: resolve audio device detection on Windows
docs: update installation instructions
feat!: migrate to new database schema (BREAKING CHANGE)
```

### Success Criteria

- ✅ Releases can be triggered by merging to main with specific commits
- ✅ Version is automatically bumped based on commit types
- ✅ Changelog is automatically generated and formatted
- ✅ Tags are automatically created
- ✅ Release notes are comprehensive and categorized
- ✅ Team understands and follows commit conventions

---

## Task #20: Telemetry/Observability Hooks

### Current State Analysis

**What We Have**:
- ✅ Basic logging (`core/logging_config.py`)
- ✅ File rotation (10MB main log, 5MB error log)
- ✅ Multiple log levels
- ✅ Structured formatter

**What's Missing**:
- ❌ Structured/JSON logging
- ❌ Error tracking service integration
- ❌ Usage metrics/analytics
- ❌ Performance monitoring
- ❌ User opt-in/opt-out mechanism
- ❌ Privacy documentation

### Goals

1. **Enhanced Logging**
   - Structured (JSON) logging for machine parsing
   - Context-aware logging (session IDs, user IDs)
   - Log aggregation readiness

2. **Error Tracking**
   - Integrate Sentry (or alternative)
   - Automatic error reporting (opt-in)
   - Stack traces and context
   - Release tracking

3. **Usage Metrics**
   - Track feature usage (anonymized)
   - Performance metrics
   - App health indicators
   - Session duration and frequency

4. **Privacy & Compliance**
   - Opt-in by default (disabled)
   - Clear privacy documentation
   - Easy opt-out mechanism
   - No PII collection
   - GDPR/CCPA compliant

### Implementation Options

#### Option A: Sentry + Structured Logging (RECOMMENDED)
**Pros**:
- ✅ Industry-standard error tracking
- ✅ Free tier available (5K events/month)
- ✅ Python SDK well-maintained
- ✅ Release tracking built-in
- ✅ Performance monitoring included

**Cons**:
- Cloud service (privacy considerations)
- Potential costs at scale

#### Option B: Self-Hosted Solution
**Pros**:
- ✅ Full data control
- ✅ No external dependencies
- ✅ No cost concerns

**Cons**:
- ❌ Requires infrastructure
- ❌ More maintenance overhead
- ❌ Less feature-rich

#### Option C: Logs-Only Approach
**Pros**:
- ✅ Simple and privacy-friendly
- ✅ No external services
- ✅ No costs

**Cons**:
- ❌ Manual error analysis
- ❌ No aggregation or visualization
- ❌ Limited insights

### Recommended Approach: Hybrid (Sentry + Enhanced Logging)

**Estimated Effort**: 5 days
- Day 1: Enhanced logging setup
- Day 2: Sentry integration
- Day 3: Metrics collection
- Day 4: Privacy mechanisms
- Day 5: Documentation and testing

**Architecture**:

```
┌─────────────────────────────────────────────┐
│          Voice Recorder Pro                 │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Telemetry Manager (Opt-In Check)   │  │
│  └──────────────────────────────────────┘  │
│           │              │           │      │
│           ├──────────────┼───────────┤      │
│           ▼              ▼           ▼      │
│  ┌──────────────┐  ┌──────────┐  ┌──────┐ │
│  │   Logging    │  │  Sentry  │  │Metrics│ │
│  │   (Always)   │  │ (Opt-In) │  │(Local)│ │
│  └──────────────┘  └──────────┘  └──────┘ │
│           ▼              ▼           ▼      │
│  ┌──────────────┐  ┌──────────┐  ┌──────┐ │
│  │  logs/*.log  │  │  Sentry  │  │SQLite│ │
│  │              │  │  Cloud   │  │  DB  │ │
│  └──────────────┘  └──────────┘  └──────┘ │
└─────────────────────────────────────────────┘
```

### Implementation Steps

#### Phase 1: Enhanced Logging (Day 1)

1. **Add Structured Logging**
   ```python
   # core/structured_logging.py
   import json
   import logging
   from datetime import datetime
   from typing import Any, Dict
   
   class StructuredLogger:
       def log_event(self, event_type: str, data: Dict[str, Any]):
           log_entry = {
               "timestamp": datetime.utcnow().isoformat(),
               "event_type": event_type,
               "data": data,
               "version": APP_VERSION
           }
           logging.info(json.dumps(log_entry))
   ```

2. **Add Context Manager**
   ```python
   # core/telemetry_context.py
   from contextvars import ContextVar
   
   session_id: ContextVar[str] = ContextVar("session_id")
   user_id: ContextVar[str] = ContextVar("user_id", default="anonymous")
   ```

#### Phase 2: Sentry Integration (Day 2)

1. **Install Sentry SDK**
   ```bash
   pip install sentry-sdk
   ```

2. **Configure Sentry**
   ```python
   # core/telemetry_config.py
   import sentry_sdk
   from sentry_sdk.integrations.logging import LoggingIntegration
   
   def init_sentry(dsn: str, environment: str):
       if is_telemetry_enabled():
           sentry_sdk.init(
               dsn=dsn,
               environment=environment,
               traces_sample_rate=0.1,
               profiles_sample_rate=0.1,
               before_send=filter_pii,
           )
   ```

3. **Add Error Boundary**
   ```python
   # core/error_handler.py
   from sentry_sdk import capture_exception
   
   def handle_error(error: Exception, context: Dict):
       logging.error(f"Error: {error}", extra=context)
       if is_telemetry_enabled():
           capture_exception(error)
   ```

#### Phase 3: Metrics Collection (Day 3)

1. **Define Metrics Schema**
   ```python
   # core/metrics.py
   from dataclasses import dataclass
   from enum import Enum
   
   class EventType(Enum):
       APP_START = "app_start"
       RECORDING_START = "recording_start"
       RECORDING_STOP = "recording_stop"
       EXPORT_FILE = "export_file"
       CLOUD_UPLOAD = "cloud_upload"
   
   @dataclass
   class MetricEvent:
       event_type: EventType
       duration_ms: int = None
       success: bool = True
       metadata: dict = None
   ```

2. **Create Metrics Collector**
   ```python
   # core/metrics_collector.py
   import sqlite3
   from pathlib import Path
   
   class MetricsCollector:
       def __init__(self, db_path: Path):
           self.db_path = db_path
           self._init_db()
       
       def record_event(self, event: MetricEvent):
           # Store locally, never send PII
           pass
       
       def get_summary(self) -> Dict:
           # Provide aggregated stats for user
           pass
   ```

#### Phase 4: Privacy Mechanisms (Day 4)

1. **Opt-In/Opt-Out System**
   ```python
   # core/privacy_manager.py
   class PrivacyManager:
       def __init__(self, config_path: Path):
           self.config = self._load_config(config_path)
       
       def is_telemetry_enabled(self) -> bool:
           return self.config.get("telemetry_enabled", False)
       
       def enable_telemetry(self):
           self.config["telemetry_enabled"] = True
           self._save_config()
       
       def disable_telemetry(self):
           self.config["telemetry_enabled"] = False
           self._save_config()
       
       def get_consent_status(self) -> Dict:
           return {
               "telemetry": self.is_telemetry_enabled(),
               "error_tracking": self.config.get("error_tracking", False),
               "usage_metrics": self.config.get("usage_metrics", False)
           }
   ```

2. **First-Run Dialog**
   ```python
   # UI dialog to request consent
   # Clear explanation of what's collected
   # Easy to change later in settings
   ```

3. **PII Filter**
   ```python
   # core/pii_filter.py
   import re
   
   def filter_pii(event, hint):
       """Filter PII before sending to Sentry"""
       # Remove file paths
       # Remove usernames
       # Remove IP addresses
       # Keep only necessary context
       return event
   ```

#### Phase 5: Documentation (Day 5)

1. **Create Privacy Policy**
   ```markdown
   # docs/PRIVACY.md
   - What data is collected
   - How it's used
   - How to opt-in/opt-out
   - Data retention
   - Third-party services (Sentry)
   ```

2. **Update User Documentation**
   ```markdown
   # docs/TELEMETRY.md
   - Benefits of telemetry
   - What gets collected
   - How to enable/disable
   - Viewing your data
   ```

3. **Developer Documentation**
   ```markdown
   # docs/dev/TELEMETRY_DEV.md
   - How to add new metrics
   - Testing telemetry locally
   - Sentry dashboard access
   ```

### Configuration Structure

```toml
# pyproject.toml or config.toml
[telemetry]
enabled = false  # Opt-in by default
error_tracking = false
usage_metrics = false
sentry_dsn = ""  # Set via env var in production
environment = "development"

[telemetry.collection]
# What events to track
app_lifecycle = true
recording_events = true
export_events = true
cloud_sync_events = true

[telemetry.privacy]
anonymize_paths = true
collect_system_info = true  # OS, Python version, etc.
collect_hardware_info = false  # CPU, RAM, etc.
retention_days = 90
```

### Environment Variables

```bash
# .env.example
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
TELEMETRY_ENABLED=false  # Default off
```

### Success Criteria

- ✅ Structured logging implemented and working
- ✅ Sentry integration functional (when enabled)
- ✅ Metrics collection stores data locally
- ✅ Opt-in mechanism works in UI
- ✅ No PII is collected or transmitted
- ✅ Privacy documentation is complete
- ✅ Users can view/export their metrics
- ✅ Error reports include relevant context
- ✅ Performance impact is minimal (<5% overhead)

---

## Implementation Priority

### Recommended Order

1. **Task #20 First** (5 days)
   - Provides immediate debugging value
   - Helps monitor v2.1.0 in the wild
   - Foundation for future product decisions
   - Can be deployed incrementally

2. **Task #19 Second** (3 days)
   - Builds on stable telemetry
   - Requires team adoption of conventions
   - Benefits are more procedural

### Parallel Work Option

If we have capacity, we could work in parallel:
- **Track A**: Enhanced logging + metrics (Task #20, Days 1-3)
- **Track B**: Release automation setup (Task #19, Days 1-3)
- **Integration**: Combine both (Days 4-5)

---

## Risks & Mitigation

### Task #19 Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Team doesn't adopt commit conventions | High | Medium | Training, templates, commit-msg hooks |
| Breaking existing workflows | Medium | Low | Test thoroughly, gradual rollout |
| Version bumping errors | High | Low | Extensive testing, rollback plan |

### Task #20 Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Privacy concerns from users | High | Medium | Opt-in by default, clear docs |
| Performance impact | Medium | Low | Async logging, local caching |
| Sentry costs | Low | Medium | Free tier sufficient, monitor usage |
| PII leakage | Critical | Low | PII filters, code review, testing |

---

## Dependencies

### Task #19 Dependencies
- ✅ Task #18 (Release workflow) - COMPLETE
- Python semantic release package
- Team understanding of conventional commits

### Task #20 Dependencies
- ✅ Task #11 (Test infrastructure) - COMPLETE
- Sentry account (free tier)
- Privacy policy review
- UI for consent dialog

---

## Timeline

### Conservative Estimate (Sequential)

```
Week 1: Task #20 - Telemetry/Observability
├─ Day 1: Enhanced logging
├─ Day 2: Sentry integration
├─ Day 3: Metrics collection
├─ Day 4: Privacy mechanisms
└─ Day 5: Documentation & testing

Week 2: Task #19 - Release Automation
├─ Day 1: PSR setup & configuration
├─ Day 2: Workflow updates
└─ Day 3: Documentation & rollout

Week 3: Buffer & Integration
├─ Integration testing
├─ Documentation polish
└─ Team onboarding
```

**Total**: 13-15 days (2.5-3 weeks)

### Optimistic Estimate (Parallel)

```
Week 1: Both tasks in parallel
├─ Days 1-3: Core implementation
└─ Days 4-5: Integration & testing

Week 2: Documentation & Rollout
├─ Day 1-2: Documentation
└─ Day 3-5: Testing & rollout
```

**Total**: 8-10 days (1.5-2 weeks)

---

## Next Steps

1. **Decision Point**: Sequential or parallel?
2. **Setup**: Create feature branches
3. **Task #20 Start**: Enhanced logging
4. **Checkpoint**: Review after Day 3
5. **Task #19 Start**: After Task #20 or in parallel
6. **Final Review**: Before merging to main

---

**Document Version**: 1.0  
**Created**: October 16, 2025  
**Status**: Planning Complete - Ready for Execution  
**Recommended Start**: Task #20 (Telemetry) first
