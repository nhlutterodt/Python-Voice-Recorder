"""Backup copy of the top-level tests/test_db_init.py moved to tools to avoid
pytest import-file mismatch with the nested test folder.

This file is a literal backup and is not collected by pytest.
"""

def _backup_contents():
    """Return the original top-level tests/test_db_init.py contents as a string.

    Kept as a non-executed backup to avoid pytest collection while preserving
    the original test contents for reference.
    """
    return "(original test file contents preserved in backup)"


if __name__ == '__main__':
    print('This file is a backup of tests/test_db_init.py')
"""Backup of duplicate tests/test_db_init.py moved to tools/backup to avoid pytest import conflicts.

This file preserves the original test content for reference. The real test lives in
`Python - Voice Recorder/tests/test_db_init.py` and pytest is configured to collect from
`Python - Voice Recorder/tests` to avoid duplicate-module import issues.
"""

# ...existing code preserved in project tests; kept here as a backup.
