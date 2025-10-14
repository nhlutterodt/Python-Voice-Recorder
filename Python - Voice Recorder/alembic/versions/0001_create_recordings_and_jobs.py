"""create recordings and jobs tables

Revision ID: 0001_create_recordings_and_jobs
Revises: 
Create Date: 2025-10-09 13:15:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_recordings_and_jobs'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # recordings table
    op.create_table(
        'recordings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('stored_filename', sa.String(), nullable=False, unique=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('filesize_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('checksum', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('sync_status', sa.String(), nullable=True, server_default='unsynced'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True),
    )

    # jobs table used by sqlite job queue helper
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_iso', sa.String(), nullable=True),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('drive_file_id', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('jobs')
    op.drop_table('recordings')
