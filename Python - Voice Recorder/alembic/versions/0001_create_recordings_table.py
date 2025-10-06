"""Initial migration: create recordings table

Revision ID: 0001_create_recordings_table
Revises: 
Create Date: 2025-10-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_recordings_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'recordings',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('filename', sa.String, nullable=False),
        sa.Column('stored_filename', sa.String, nullable=False, unique=True),
        sa.Column('title', sa.String, nullable=True),
        sa.Column('duration', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('filesize_bytes', sa.BigInteger, nullable=True),
        sa.Column('mime_type', sa.String, nullable=True),
        sa.Column('checksum', sa.String, nullable=True),
        sa.Column('status', sa.String, nullable=True, server_default='active'),
        sa.Column('sync_status', sa.String, nullable=True, server_default='unsynced'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('recordings')
