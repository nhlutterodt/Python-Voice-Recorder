# Cleanup Action Plan

## Files to Consider for Cleanup/Consolidation

### Test Files
- [ ] `tests/test_enhanced_file_storage_premigration.py` - Pre-migration validation, may be redundant now
- [ ] `tests/test_imports.py` - Basic import tests, consider consolidating 
- [ ] `validate_task_1_2.py` - Task-specific validation, archive after Phase 2 complete

### Documentation Consolidation Opportunities
- [ ] `docs/ENHANCED_FILE_STORAGE_REFACTORING_PLAN.md` - File storage specific plan
- [ ] `docs/STORAGE_CONFIG_REFACTORING_PLAN.md` - Storage config specific plan  
- [ ] `docs/BACKEND_ENHANCEMENT_PLAN.md` - Overall enhancement plan

**Recommendation**: Keep all three as they serve different purposes, but ensure they're synchronized.

### Validation Scripts
- [ ] `scripts/validate_phase_1.py` - Phase 1 validation 
- [ ] `scripts/validate_phase_2.py` - Phase 2 validation
- [ ] `scripts/comprehensive_analysis.py` - Overall analysis

**Recommendation**: Archive phase-specific validators, keep comprehensive analysis.

## Cleanup Actions

### Immediate (Safe to do now)
1. Archive completed phase validation scripts to `scripts/archive/`
2. Move pre-migration tests to `tests/archive/`  
3. Update import statements in any remaining legacy code

### Consider Later (After Phase 3)
1. Consolidate overlapping documentation
2. Remove redundant validation files
3. Cleanup temporary task validation files

## Files to Keep (Important)
- All production code in `services/file_storage/`
- All current test suites for active components
- Phase validation reports (historical record)
- Main enhancement plan documentation
- Backward compatibility facade (`services/enhanced_file_storage.py`)
