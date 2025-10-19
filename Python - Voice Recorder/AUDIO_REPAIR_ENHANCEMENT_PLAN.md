# Audio Repair Enhancement Plan

## Overview
Integrate audio file repair functionality directly into the GUI for seamless recovery of corrupted audio files. This enhancement provides two complementary user workflows: **inline repair** (when an error occurs) and **dedicated tool** (proactive batch repair).

---

## Proposed Architecture: HYBRID SOLUTION

### Design Philosophy
**Single Source of Truth**: Extract repair logic into a reusable service layer that both CLI and GUI can use.

```
┌─────────────────────────────────────────────────────┐
│          services/audio_repair_service.py            │
│  (Core repair logic - used by CLI and GUI)          │
│  - repair_audio_file(input, output)                  │
│  - get_file_corruption_info(file)                    │
│  - validate_audio_file(file)                         │
└─────────────────────────────────────────────────────┘
         ↑                            ↑
         │                            │
    ┌────┴─────────────┐   ┌─────────┴─────────────┐
    │                  │   │                       │
┌───┴────────────────┐ │   │ ┌────────────────────┐│
│ tools/audio_       │ │   │ │ src/audio_repair   ││
│ repair.py          │ │   │ │ _widget.py         ││
│ (CLI Tool)         │ │   │ │ (GUI Interface)    ││
│                    │ │   │ │                    ││
│ Command-line       │ │   │ │ - File browser     ││
│ batch repair       │ │   │ │ - Progress display ││
│ interface          │ │   │ │ - Batch processing ││
└────────────────────┘ │   │ │ - Results summary  ││
                       │   │ └────────────────────┘│
                       │   │                       │
                       └───┴─────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Refactor & Extract (Foundation) - ~1 hour
**Goal**: Create reusable service layer

**Files to Create:**
- `services/audio_repair_service.py` - Core repair logic

**Files to Modify:**
- `tools/audio_repair.py` - Use service layer instead of duplicate logic

**Key Functions:**
```python
# services/audio_repair_service.py
def repair_audio_file(input_path: str, output_path: str) -> dict:
    """
    Repair corrupted audio file by re-encoding to standard format.
    
    Returns: {
        'success': bool,
        'input_file': str,
        'output_file': str,
        'original_size': int,
        'repaired_size': int,
        'error': str or None,
        'format_info': {
            'channels': int,
            'sample_width': int,
            'frame_rate': int
        }
    }
    """

def validate_audio_file(file_path: str) -> dict:
    """Check if file is corrupted without attempting repair."""
    
def get_corruption_info(file_path: str) -> str:
    """Get human-readable description of file corruption."""
```

---

### Phase 2: Inline Repair (Quick Win) - ~1-2 hours
**Goal**: "Repair & Retry" button in error dialog

**Files to Modify:**
- `src/enhanced_editor.py` - Update `on_load_error()` handler

**UX Flow:**
```
[User tries to open file]
         ↓
[File fails to load]
         ↓
[Error Dialog appears]
┌─────────────────────────────────────────┐
│ Failed to load audio file                │
│                                         │
│ The file appears to be corrupted.       │
│                                         │
│ [Repair & Retry]  [Cancel]              │
└─────────────────────────────────────────┘
         ↓
   [Clicked "Repair & Retry"]
         ↓
┌─────────────────────────────────────────┐
│ Repairing audio file...                 │
│ ████████░░░░░░░░░░░░ 45%                │
│                                         │
│ This may take a few seconds...          │
└─────────────────────────────────────────┘
         ↓
   [Repair completes]
         ↓
[File loads into editor successfully!]
```

**Implementation Details:**
1. Add "Repair & Retry" button to error dialog
2. Show progress dialog during repair (blocking)
3. On success: Automatically retry loading repaired file
4. On failure: Show detailed error with manual recovery steps
5. Save repaired file alongside original (or prompt for location)

**Code Pattern:**
```python
def on_load_error(self, error_message: str):
    """Enhanced error handler with inline repair option"""
    
    # Create error dialog with "Repair & Retry" button
    reply = QMessageBox.warning(
        self,
        "Failed to Load Audio",
        "The file appears to be corrupted.\n\nWould you like to repair it?",
        QMessageBox.StandardButtons.Yes | QMessageBox.StandardButtons.No,
    )
    
    if reply == QMessageBox.StandardButtons.Yes:
        # Launch repair process
        self.repair_and_retry_loading(self.current_file_path)
```

---

### Phase 3: Dedicated Repair Tool (Full Featured) - ~2-3 hours
**Goal**: Professional audio repair interface accessible from menu

**Files to Create:**
- `src/audio_repair_widget.py` - Dedicated repair UI window

**Files to Modify:**
- `src/enhanced_main.py` - Add menu item: `Tools → Audio Repair Tool`

**UI Components:**
```
┌────────────────────────────────────────────────────┐
│  Audio Repair Tool                            [✕] │
├────────────────────────────────────────────────────┤
│                                                    │
│  Input:                                            │
│  ┌─ Single File ───────────────────────────────┐  │
│  │ [📁] Select audio file...                   │  │
│  │ Current: (no file selected)                 │  │
│  └────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ or Directory ───────────────────────────────┐ │
│  │ [📁] Select directory...                     │ │
│  │ Current: (no directory selected)            │ │
│  │ [✓] Include subdirectories                  │ │
│  └────────────────────────────────────────────┘  │
│                                                    │
│  Output Options:                                   │
│  [•] Save as .repaired.wav (keep original)       │
│  [○] Replace original (backup first)              │
│  [○] Save to custom location: [_______]           │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ Files to Process:                            │ │
│  │                                              │ │
│  │ ✓ recording_20251018.wav          7.2 MB   │ │
│  │ ✓ recording_20251017.wav          5.1 MB   │ │
│  │ ⚠ corrupted_file.wav             CORRUPTED │ │
│  │ ○ good_file.wav                   CLEAN    │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  Progress:                                         │
│  [████████████░░░░░░░░░░░░░░░░░░░░░] 40% (2/5)   │
│  Currently repairing: recording_20251017.wav       │
│                                                    │
│            [Start Repair]  [Clear]  [Cancel]      │
│                                                    │
│  Results (after completion):                       │
│  ✓ 2 files successfully repaired                  │
│  ⚠ 1 file skipped (already valid)                │
│  ✗ 1 file failed (too corrupted)                 │
│                                                    │
│  [Open in Editor]  [Show in Explorer]  [Close]   │
└────────────────────────────────────────────────────┘
```

**Key Features:**
1. **File Selection**
   - Single file picker
   - Directory browser with recursive option
   - File filtering (.wav only)

2. **File Status Detection**
   - ✓ Valid files (green) - can skip
   - ⚠ Corrupted files (orange) - need repair
   - Duplicate files (gray) - skip duplicates

3. **Repair Processing**
   - Batch repair with progress bar
   - Real-time status updates
   - Thread-based to keep UI responsive

4. **Output Handling**
   - Keep originals with `.repaired.wav` suffix
   - Backup originals before replacing
   - Custom output directory

5. **Results Dashboard**
   - Summary: X repaired, Y skipped, Z failed
   - Detailed log of each file
   - Open repaired file in editor
   - Show in file explorer

---

## Implementation Details by Phase

### Phase 1: Service Layer

```python
# services/audio_repair_service.py

from pathlib import Path
from typing import Optional
import subprocess

class AudioRepairService:
    """Service for repairing corrupted audio files"""
    
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 2
    DEFAULT_CODEC = 'pcm_s16le'
    
    @staticmethod
    def repair_audio_file(
        input_path: str,
        output_path: str,
        force: bool = False
    ) -> dict:
        """Repair audio file using FFmpeg"""
        # Implementation: Use ffmpeg to re-encode
        
    @staticmethod
    def validate_audio_file(file_path: str) -> bool:
        """Check if audio file is valid"""
        # Try loading with pydub
        
    @staticmethod
    def batch_repair(
        file_paths: list[str],
        output_dir: Optional[str] = None,
        on_progress: Optional[callable] = None
    ) -> dict:
        """Repair multiple files with progress callback"""
        # Implementation: Loop through files with progress
```

### Phase 2: Inline Repair Integration

```python
# In src/enhanced_editor.py

from services.audio_repair_service import AudioRepairService

def on_load_error(self, error_message: str):
    """Enhanced error handler with inline repair"""
    
    # Show dialog with repair option
    reply = QMessageBox.question(
        self,
        "Failed to Load Audio",
        f"{error_message}\n\nWould you like to attempt repair?",
        QMessageBox.StandardButtons.Yes | QMessageBox.StandardButtons.No,
    )
    
    if reply == QMessageBox.Yes:
        self.attempt_repair_and_reload()

def attempt_repair_and_reload(self):
    """Repair file and retry loading"""
    
    # Show progress
    progress = QProgressDialog("Repairing audio file...", None, 0, 0, self)
    progress.setModal(True)
    progress.show()
    QApplication.processEvents()
    
    try:
        result = AudioRepairService.repair_audio_file(
            self.current_file_path,
            output_path=self.current_file_path + ".repaired.wav"
        )
        
        if result['success']:
            # Retry loading repaired file
            repaired_path = result['output_file']
            self.load_audio_file(repaired_path)
            progress.close()
            
            QMessageBox.information(
                self,
                "Repair Successful",
                f"File repaired successfully!\n\n"
                f"Original: {self.current_file_path}\n"
                f"Repaired: {repaired_path}"
            )
        else:
            progress.close()
            QMessageBox.critical(
                self,
                "Repair Failed",
                f"Could not repair file: {result['error']}"
            )
    
    except Exception as e:
        progress.close()
        QMessageBox.critical(self, "Error", f"Repair failed: {e}")
```

### Phase 3: Dedicated Widget

```python
# In src/audio_repair_widget.py

from PySide6.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QListWidget
from services.audio_repair_service import AudioRepairService

class AudioRepairWidget(QDialog):
    """Dedicated interface for repairing audio files"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Repair Tool")
        self.setup_ui()
        self.service = AudioRepairService()
    
    def setup_ui(self):
        """Build the UI layout"""
        # File selection
        # Directory selection
        # Output options radio buttons
        # File list widget
        # Progress bar
        # Buttons: Start, Clear, Cancel
    
    def start_repair(self):
        """Begin repair process"""
        files = self.get_selected_files()
        
        def on_progress(current, total, current_file):
            self.progress_bar.setValue(int(current/total * 100))
            self.status_label.setText(f"Processing {current_file}...")
        
        results = self.service.batch_repair(
            files,
            on_progress=on_progress
        )
        
        self.show_results(results)
```

---

## Testing Strategy

### Phase 1
- ✓ Unit tests for `AudioRepairService`
- ✓ Test repair with various corruption types
- ✓ Test batch processing

### Phase 2
- ✓ Integration tests with `enhanced_editor.py`
- ✓ Test repair + retry workflow
- ✓ Test error handling

### Phase 3
- ✓ Widget UI tests
- ✓ File browser integration
- ✓ Progress display accuracy
- ✓ Results summary correctness

---

## Timeline

| Phase | Task | Estimated Time | Cumulative |
|-------|------|-----------------|-----------|
| 1 | Extract service layer | 1 hour | 1 hour |
| 2 | Inline repair dialog | 1.5 hours | 2.5 hours |
| 3 | Dedicated tool UI | 2.5 hours | 5 hours |
| Testing | Unit + Integration | 1 hour | 6 hours |
| **Total** | | | **~6 hours** |

---

## User Benefits

✅ **Zero Data Loss** - Corrupted files can be recovered with one click
✅ **Seamless UX** - Repair happens transparently when loading fails
✅ **Batch Capability** - Fix multiple files at once
✅ **Proactive** - Can repair known-bad files before using them
✅ **Transparent** - Clear feedback on what's being repaired
✅ **Safe** - Originals kept as backup

---

## Questions for User

1. **Which phase should we start with?**
   - Option A: Start with Phase 1 + 2 (Quick inline repair, ~2.5 hours)
   - Option B: Start with Phase 1 + 2 + 3 (Complete solution, ~6 hours)
   - Option C: Just Phase 3 (Dedicated tool only, skip inline repair)

2. **Default behavior for repaired files:**
   - Option A: Always save as `.repaired.wav` (keep original)
   - Option B: Prompt user each time
   - Option C: User preference setting

3. **Should repaired files auto-open in editor?**
   - Option A: Yes, always auto-open
   - Option B: Prompt user
   - Option C: No, user decides

---

## Recommendation

**I recommend starting with Phase 1 + 2** (Inline Repair):
- Quick implementation (~2.5 hours)
- Addresses the immediate pain point (clicking "Repair & Retry" when error occurs)
- Foundation for Phase 3 if needed later
- 80/20 solution: most users will just need the inline repair

Then if you want more advanced features, Phase 3 can be added independently.

**Would you like to proceed with this plan? Which phases interest you most?**
