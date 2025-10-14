# Database Migrations Guide

## Overview

Voice Recorder Pro uses Alembic for database schema migrations. This ensures that database changes are applied safely and consistently across different installations.

## Files

- `alembic.ini` - Alembic configuration
- `alembic/` - Migration scripts directory
- `migrate_db.py` - Convenient migration runner script

## For End Users

### Upgrading Database

When you update Voice Recorder Pro, simply run:

```bash
python migrate_db.py
```

This script will:
1. 📦 Automatically backup your current database
2. ⚡ Apply any pending migrations
3. ✅ Confirm successful completion
4. 💾 Restore from backup if anything goes wrong

## For Developers

### Creating New Migrations

1. **Make changes to models** in `models/recording.py` or other model files

2. **Generate migration** (auto-detects changes):
   ```bash
   alembic revision --autogenerate -m "Description of changes"
   ```

3. **Review the generated migration** in `alembic/versions/`

4. **Test the migration**:
   ```bash
   alembic upgrade head
   ```

### Manual Migrations

For complex changes that can't be auto-generated:

```bash
# Create empty migration
alembic revision -m "Description"

# Edit the generated file in alembic/versions/
# Add upgrade() and downgrade() functions
```

### Common Commands

```bash
# Check current migration state
alembic current

# Apply all pending migrations
alembic upgrade head

# Apply migrations up to specific revision
alembic upgrade <revision_id>

# Downgrade one migration
alembic downgrade -1

# Show migration history
alembic history

# Show SQL without executing
alembic upgrade head --sql
```

## Migration History

- `cabc59ea0c9d` - Initial recording model (basic fields)
- `4ae620c1c938` - Add metadata columns (checksum, sync status, etc.)

## Troubleshooting

### Migration Fails

1. **Check logs** - Alembic provides detailed error messages
2. **Use backup** - The `migrate_db.py` script automatically creates backups
3. **Manual recovery**:
   ```bash
   # Restore from backup
   cp db/app_backup_YYYYMMDD_HHMMSS.db db/app.db
   
   # Check current state
   alembic current
   
   # Stamp to correct revision if needed
   alembic stamp <revision_id>
   ```

### Schema Conflicts

If you get "table already exists" or "column already exists" errors:

1. Check actual database schema:
   ```python
   import sqlite3
   conn = sqlite3.connect('db/app.db')
   print(conn.execute('PRAGMA table_info(recordings)').fetchall())
   ```

2. Stamp database to match actual state:
   ```bash
   alembic stamp head
   ```

## Best Practices

### For Schema Changes

1. **Always create migrations** - Don't modify schema directly
2. **Test migrations** - Run on copy of production data first
3. **Review generated migrations** - Auto-generated isn't always perfect
4. **Add data migration logic** - Handle existing data when changing schemas

### For Production

1. **Backup before migrations** - Use `migrate_db.py` or manual backup
2. **Test rollback** - Ensure downgrade functions work
3. **Plan maintenance windows** - Large migrations may take time
4. **Monitor disk space** - SQLite recreates entire file for some operations

### SQLite Limitations

SQLite has limited ALTER TABLE support:
- ✅ Can add columns
- ❌ Cannot drop columns directly
- ❌ Cannot modify column types
- ❌ Cannot add NOT NULL constraints to existing columns

For complex changes, use table recreation pattern:
1. Create new table with desired schema
2. Copy data from old table
3. Drop old table
4. Rename new table

## Integration with Application

The Recording model now includes these metadata fields:
- `stored_filename` - UUID-based filename for storage
- `filesize_bytes` - File size in bytes
- `mime_type` - MIME type of the audio file
- `checksum` - SHA256 hash for integrity verification
- `sync_status` - Cloud sync state (unsynced, syncing, synced, failed)
- `last_synced_at` - Timestamp of last successful sync
- `modified_at` - Timestamp of last modification

These fields enable:
- 🔒 Data integrity verification (checksums)
- ☁️ Cloud synchronization tracking
- 📊 Storage analytics and cleanup
- 🔍 Duplicate detection and deduplication
