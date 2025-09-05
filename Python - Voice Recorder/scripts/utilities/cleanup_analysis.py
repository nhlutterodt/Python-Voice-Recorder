#!/usr/bin/env python3
"""
Project Cleanup Analysis and Recommendations
Identifies files that can be safely deleted now that backend enhancements are complete
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

class ProjectCleanupAnalyzer:
    """Analyze project files for cleanup opportunities"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
    def analyze_files(self) -> Dict[str, List[Tuple[str, str]]]:
        """Analyze all files and categorize for cleanup"""
        
        cleanup_plan = {
            "SAFE_TO_DELETE": [],
            "PROBABLY_DELETE": [], 
            "KEEP_ESSENTIAL": [],
            "KEEP_TESTS": [],
            "NEEDS_REVIEW": []
        }
        
        # SAFE TO DELETE - Development task validation scripts (completed)
        task_validation_files = [
            ("validate_task_1_1.py", "Task 1.1 validation - Enhanced Storage Service Structure (COMPLETED)"),
            ("validate_task_1_2.py", "Task 1.2 validation - Storage Configuration Classes (COMPLETED)"),
            ("validate_task_1_3.py", "Task 1.3 validation - File Metadata Calculation Utilities (COMPLETED)"),
            ("validate_task_2_1.py", "Task 2.1 validation - StorageConfig Integration (COMPLETED)"),
            ("validate_task_2_1_simple.py", "Task 2.1 simple validation - duplicate/redundant (COMPLETED)"),
        ]
        
        for file_name, reason in task_validation_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                cleanup_plan["SAFE_TO_DELETE"].append((str(file_path), reason))
        
        # PROBABLY DELETE - One-off or superseded scripts
        probably_delete_files = [
            ("test_exception_handling.py", "One-off exception test - functionality covered by test_backend_enhancements.py"),
            ("analyze_storage.py", "Storage analysis script - was for development analysis, not ongoing testing"),
        ]
        
        for file_name, reason in probably_delete_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                cleanup_plan["PROBABLY_DELETE"].append((str(file_path), reason))
        
        # KEEP ESSENTIAL - Critical ongoing scripts
        essential_files = [
            ("test_backend_enhancements.py", "Comprehensive backend enhancement tests - CRITICAL for ongoing validation"),
            ("validate_implementation_completeness.py", "Comprehensive implementation validation - CRITICAL for verification"),
            ("enhanced_main.py", "Main application entry point"),
            ("enhanced_editor.py", "Enhanced audio editor - main UI component"),
            ("audio_recorder.py", "Core audio recording functionality"),
            ("audio_processing.py", "Core audio processing functionality"),
            ("performance_monitor.py", "Performance monitoring system"),
            ("backend_enhancement_tracker.py", "Backend enhancement tracking system"),
        ]
        
        for file_name, reason in essential_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                cleanup_plan["KEEP_ESSENTIAL"].append((str(file_path), reason))
        
        # KEEP TESTS - Tests directory (ongoing regression testing value)
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            for test_file in tests_dir.glob("*.py"):
                cleanup_plan["KEEP_TESTS"].append((str(test_file), "Ongoing regression tests - keep for continuous validation"))
        
        # NEEDS REVIEW - Files that might overlap or need evaluation
        review_files = [
            ("test_critical_components.py", "Comprehensive integration tests - may overlap with new tests, review for redundancy"),
        ]
        
        for file_name, reason in review_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                cleanup_plan["NEEDS_REVIEW"].append((str(file_path), reason))
        
        return cleanup_plan

def main():
    """Generate cleanup recommendations"""
    print("🧹 PROJECT CLEANUP ANALYSIS")
    print("=" * 80)
    print("Analyzing project files for cleanup opportunities...")
    print()
    
    # Analyze current directory
    current_dir = Path(__file__).parent
    analyzer = ProjectCleanupAnalyzer(str(current_dir))
    cleanup_plan = analyzer.analyze_files()
    
    # Display results
    for category, files in cleanup_plan.items():
        if not files:
            continue
            
        category_name = category.replace("_", " ").title()
        
        if category == "SAFE_TO_DELETE":
            print(f"🗑️  {category_name} ({len(files)} files)")
            print("─" * 60)
            print("These files were for incremental development validation and can be safely deleted:")
        elif category == "PROBABLY_DELETE":
            print(f"🤔 {category_name} ({len(files)} files)")
            print("─" * 60)
            print("These files are likely no longer needed but review before deleting:")
        elif category == "KEEP_ESSENTIAL":
            print(f"✅ {category_name} ({len(files)} files)")
            print("─" * 60)
            print("These files are critical for the application and should be kept:")
        elif category == "KEEP_TESTS":
            print(f"🧪 {category_name} ({len(files)} files)")
            print("─" * 60)
            print("These test files provide ongoing value and should be kept:")
        elif category == "NEEDS_REVIEW":
            print(f"👀 {category_name} ({len(files)} files)")
            print("─" * 60)
            print("These files need manual review to determine if they can be deleted:")
        
        for file_path, reason in files:
            file_name = Path(file_path).name
            print(f"  • {file_name}")
            print(f"    └─ {reason}")
        print()
    
    # Summary and next steps
    safe_delete_count = len(cleanup_plan["SAFE_TO_DELETE"])
    probably_delete_count = len(cleanup_plan["PROBABLY_DELETE"])
    total_deletable = safe_delete_count + probably_delete_count
    
    print("📊 CLEANUP SUMMARY")
    print("─" * 40)
    print(f"Files safe to delete immediately: {safe_delete_count}")
    print(f"Files probably safe to delete: {probably_delete_count}")
    print(f"Total potential deletions: {total_deletable}")
    print(f"Essential files to keep: {len(cleanup_plan['KEEP_ESSENTIAL'])}")
    print(f"Test files to keep: {len(cleanup_plan['KEEP_TESTS'])}")
    print(f"Files needing review: {len(cleanup_plan['NEEDS_REVIEW'])}")
    
    print("\n🎯 RECOMMENDED CLEANUP ACTIONS")
    print("─" * 40)
    
    if safe_delete_count > 0:
        print("1. ✅ DELETE IMMEDIATELY - Task validation scripts:")
        for file_path, _ in cleanup_plan["SAFE_TO_DELETE"]:
            print(f"   rm \"{Path(file_path).name}\"")
    
    if probably_delete_count > 0:
        print("\n2. 🤔 REVIEW AND DELETE - One-off scripts:")
        for file_path, reason in cleanup_plan["PROBABLY_DELETE"]:
            print(f"   rm \"{Path(file_path).name}\"  # {reason}")
    
    if cleanup_plan["NEEDS_REVIEW"]:
        print("\n3. 👀 MANUAL REVIEW NEEDED:")
        for file_path, reason in cleanup_plan["NEEDS_REVIEW"]:
            print(f"   Review: {Path(file_path).name} - {reason}")
    
    print(f"\n🎉 CLEANUP BENEFIT")
    print("─" * 40)
    print(f"Removing {total_deletable} unnecessary files will:")
    print("• Reduce project clutter and improve navigation")
    print("• Eliminate confusion about which tests to run")
    print("• Focus attention on the essential, production-ready components")
    print("• Maintain only the comprehensive validation scripts we created")
    
    return cleanup_plan

if __name__ == "__main__":
    main()
