"""add job progress and cancellation columns

Revision ID: 0002_add_job_progress_columns
Revises: 0001_create_recordings_and_jobs
Create Date: 2025-10-09 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import sqlite3

# revision identifiers, used by Alembic.
revision = '0002_add_job_progress_columns'
down_revision = '0001_create_recordings_and_jobs'
branch_labels = None
depends_on = None


def upgrade():
    # Add new nullable columns for job progress and cancellation support.
    # Some developer runs previously created columns via metadata.create_all or
    # runtime code; add the columns only if they don't already exist. SQLite
    # will raise an OperationalError for duplicate columns, so we catch and
    # ignore that specific error.
    conn = op.get_bind()
    statements = [
        "ALTER TABLE jobs ADD COLUMN started_iso TEXT",
        "ALTER TABLE jobs ADD COLUMN finished_iso TEXT",
        "ALTER TABLE jobs ADD COLUMN uploaded_bytes BIGINT DEFAULT 0",
        "ALTER TABLE jobs ADD COLUMN total_bytes BIGINT",
        "ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER DEFAULT 0",
    ]
    for sql in statements:
        try:
            conn.exec_driver_sql(sql)
        except Exception as e:
            # If it's a duplicate-column error from sqlite, ignore it; otherwise
            # re-raise so migration failures are visible.
            if isinstance(e, sqlite3.OperationalError) and 'duplicate column name' in str(e).lower():
                continue
            msg = str(e).lower()
            if 'duplicate column' in msg or 'duplicate column name' in msg:
                continue
            raise


def downgrade():
    # SQLite does not support DROP COLUMN easily; attempt best-effort drops and
    # ignore failures. This downgrade is best-effort for development use.
    conn = op.get_bind()
    drop_statements = [
        # SQLite doesn't support DROP COLUMN; leaving as no-op is acceptable for dev
    ]
    for sql in drop_statements:
        try:
            conn.execute(sql)
        except Exception:
            pass
