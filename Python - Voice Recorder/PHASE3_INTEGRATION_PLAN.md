# Phase 3 Plan: Component Integration into GoogleDriveManager

## Objective
Refactor GoogleDriveManager to use the Phase 2 components (FolderManager, FileManager, StorageInfo) while maintaining 100% backward compatibility.

---

## Current GoogleDriveManager Structure (574 lines)

### Current Methods
1. `__init__(auth_manager)` - Initialize manager
2. `_get_service()` - Get/create Drive service
3. `_ensure_recordings_folder()` - Ensure recordings folder exists (DUPLICATE - will use FolderManager)
4. `list_folders(parent_id, page_size)` - List folders (DUPLICATE - will use FolderManager)
5. `create_folder(name, parent_id)` - Create folder (DUPLICATE - will use FolderManager)
6. `set_recordings_folder(folder_id)` - Set recordings folder (DUPLICATE - will use FolderManager)
7. `upload_recording(file_path, ...)` - Upload file (DUPLICATE - will use FileManager)
8. `download_recording(file_id, download_path)` - Download file (DUPLICATE - will use FileManager)
9. `list_recordings(folder_id, page_size)` - List files (DUPLICATE - will use FileManager)
10. `find_duplicate_by_content_sha256(hash)` - Find duplicate (DUPLICATE - will use FileManager)
11. `delete_recording(file_id)` - Delete file (DUPLICATE - will use FileManager)
12. Plus 50+ more lines of utilities and helpers

---

## Phase 3 Refactoring Strategy

### Step 1: Composition-Based Integration
Replace monolithic methods with component delegation:

```python
class GoogleDriveManager:
    def __init__(self, auth_manager: Any):
        self.auth_manager = auth_manager
        self._folder_manager = None  # Lazy init
        self._file_manager = None    # Lazy init
        self._storage_info = None    # Lazy init
    
    @property
    def folder_manager(self) -> GoogleFolderManager:
        if not self._folder_manager:
            from ._folder_manager import GoogleFolderManager
            self._folder_manager = GoogleFolderManager(self.auth_manager)
        return self._folder_manager
    
    @property
    def file_manager(self) -> GoogleFileManager:
        if not self._file_manager:
            from ._file_manager import GoogleFileManager
            self._file_manager = GoogleFileManager(
                self.auth_manager, 
                self.folder_manager
            )
        return self._file_manager
    
    # Maintain backward compatible methods that delegate to components
    def upload_recording(self, file_path, title=None, ...):
        return self.file_manager.upload_file(file_path, title, ...)
```

### Step 2: Backward Compatibility Layer
All public methods remain unchanged:
- Public API signatures identical
- Return types identical
- Error handling identical
- Logging identical

### Step 3: Code Reduction
Expected reduction: ~300-350 lines (extracting duplicated logic to components)

---

## Refactoring Plan

### Phase 3.1: Add Component Properties to GoogleDriveManager
- Add lazy-loading properties for components
- Initialize components on first use
- Share auth_manager with components

**Files to Modify**: `cloud/drive_manager.py`  
**Lines to Add**: ~30-40  
**Lines to Remove**: 0 (non-destructive)

### Phase 3.2: Create Delegation Methods
Replace existing folder methods with component delegation:
- `list_folders()` → delegates to `folder_manager.list_folders()`
- `create_folder()` → delegates to `folder_manager.create_folder()`
- `_ensure_recordings_folder()` → delegates to `folder_manager.ensure_recordings_folder()`
- `set_recordings_folder()` → delegates to `folder_manager.set_recordings_folder()`

**Files to Modify**: `cloud/drive_manager.py`  
**Lines to Remove**: ~80-100 (monolithic folder logic)  
**Lines to Add**: ~20-30 (delegation methods)

### Phase 3.3: Create File Operation Delegation
Replace existing file methods with component delegation:
- `upload_recording()` → delegates to `file_manager.upload_file()`
- `download_recording()` → delegates to `file_manager.download_file()`
- `list_recordings()` → delegates to `file_manager.list_files()`
- `find_duplicate_by_content_sha256()` → delegates to `file_manager.find_duplicate_by_hash()`
- `delete_recording()` → delegates to `file_manager.delete_file()`

**Files to Modify**: `cloud/drive_manager.py`  
**Lines to Remove**: ~150-200 (monolithic file logic)  
**Lines to Add**: ~30-40 (delegation methods)

### Phase 3.4: Add Storage Info Support
Add storage quota methods using StorageInfo component:
- New method: `get_storage_quota()` → delegates to `storage_info.get_storage_quota()`
- New method: `get_storage_summary()` → delegates to `storage_info.get_storage_summary()`

**Files to Modify**: `cloud/drive_manager.py`  
**Lines to Add**: ~10-15

### Phase 3.5: Remove Deprecated Helpers
Remove duplicate lazy-import helpers (now in `_lazy.py`):
- `_has_module()` - Now in `_lazy.py`
- `GOOGLE_APIS_AVAILABLE` - Now in `_lazy.py`
- `_import_build()` - Now in `_lazy.py`
- `_import_http()` - Now in `_lazy.py`

**Files to Modify**: `cloud/drive_manager.py`  
**Lines to Remove**: ~20-30 (duplicate code)

### Phase 3.6: Create Integration Tests
Create comprehensive integration tests for refactored GoogleDriveManager:
- Tests verify all delegation works correctly
- Tests verify backward compatibility
- Tests verify component initialization
- Tests verify error handling through delegation

**Files to Create**: `tests/test_drive_manager_integration.py`  
**Target Tests**: 15-20  
**Coverage Target**: >80% for refactored drive_manager.py

---

## Expected Outcomes

### Code Metrics Before (Current)
```
GoogleDriveManager: 574 lines
- Monolithic folder logic: ~100 lines
- Monolithic file logic: ~150 lines
- Duplicate helpers: ~30 lines
```

### Code Metrics After
```
GoogleDriveManager: ~250-300 lines (refactored)
- Component integration: ~30-40 lines
- Delegation methods: ~60-80 lines
- Removed duplicates: -30 lines
- Cleaner structure: ~60-90 lines saved
```

### Reduction: ~250-300 lines eliminated!

---

## Backward Compatibility Verification

All existing public methods remain:
- ✅ `upload_recording()` - Same signature, same behavior
- ✅ `download_recording()` - Same signature, same behavior
- ✅ `list_recordings()` - Same signature, same behavior
- ✅ `list_folders()` - Same signature, same behavior
- ✅ `create_folder()` - Same signature, same behavior
- ✅ `set_recordings_folder()` - Same signature, same behavior
- ✅ `delete_recording()` - Same signature, same behavior

---

## Phase 3 Workflow

### 1. Component Property Integration (~30 min)
- Add lazy-loading properties for FolderManager, FileManager, StorageInfo
- Test component initialization
- Verify auth_manager sharing

### 2. Folder Operations Refactoring (~45 min)
- Replace folder methods with delegation
- Update existing tests to verify delegation
- Ensure zero behavior change

### 3. File Operations Refactoring (~60 min)
- Replace file methods with delegation
- Update existing tests to verify delegation
- Handle edge cases in delegation

### 4. Integration & New Features (~30 min)
- Add storage quota methods
- Create integration tests
- Verify everything works

### 5. Testing & Verification (~30 min)
- Run all Phase 1 tests (73) - should pass
- Run all Phase 2 tests (40) - should pass
- Run new integration tests (15+) - should pass
- Verify backward compatibility

### 6. Documentation (~20 min)
- Create Phase 3 completion report
- Document refactoring changes
- Record lessons learned

**Total Estimated Time: ~3-4 hours**

---

## Success Criteria

✅ All Phase 1 tests still passing (73/73)  
✅ All Phase 2 tests still passing (40/40)  
✅ All public API methods unchanged  
✅ Return types unchanged  
✅ Error handling unchanged  
✅ Code quality maintained  
✅ 15+ integration tests passing  
✅ Overall coverage >80%  
✅ Documentation complete  

---

## Risk Mitigation

### Risk: Breaking changes to public API
**Mitigation**: Keep all public methods with identical signatures and behavior
**Verification**: Run existing code against refactored version

### Risk: Component initialization failures
**Mitigation**: Use lazy-loading properties with defensive checks
**Verification**: Unit tests for each property initialization

### Risk: Performance regression
**Mitigation**: Components use same caching strategies as original code
**Verification**: No additional API calls introduced

### Risk: Integration failures
**Mitigation**: Create comprehensive integration tests
**Verification**: All tests pass before release

---

## Ready to Begin Phase 3

All prerequisites met:
- ✅ Components tested and verified (40/40 tests)
- ✅ Phase 1 utilities working (73/73 tests)
- ✅ Architecture understood
- ✅ Refactoring plan clear
- ✅ Success criteria defined

**Begin Phase 3.1: Add Component Properties to GoogleDriveManager**

---

Generated: 2025-01-09  
Status: ⏳ READY TO BEGIN
