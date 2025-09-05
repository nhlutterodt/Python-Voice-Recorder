"""Add metadata columns to recording

Revision ID: 4ae620c1c938
Revises: cabc59ea0c9d
Create Date: 2025-09-04 23:09:56.749702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ae620c1c938'
down_revision: Union[str, Sequence[str], None] = 'cabc59ea0c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new metadata columns to recordings table
    # Note: SQLite has limited ALTER TABLE support, so we add columns as nullable
    # and handle constraints in application logic
    op.add_column('recordings', sa.Column('stored_filename', sa.String(), nullable=True))
    op.add_column('recordings', sa.Column('filesize_bytes', sa.BigInteger(), nullable=True))
    op.add_column('recordings', sa.Column('mime_type', sa.String(), nullable=True))
    op.add_column('recordings', sa.Column('checksum', sa.String(), nullable=True))
    op.add_column('recordings', sa.Column('sync_status', sa.String(), nullable=True))
    op.add_column('recordings', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recordings', sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True))
    
    # Update existing records with default values
    op.execute("UPDATE recordings SET sync_status = 'unsynced' WHERE sync_status IS NULL")
    
    # Populate stored_filename for existing records based on filename
    op.execute("""
        UPDATE recordings 
        SET stored_filename = filename 
        WHERE stored_filename IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the new columns (SQLite will handle this)
    op.drop_column('recordings', 'modified_at')
    op.drop_column('recordings', 'last_synced_at')
    op.drop_column('recordings', 'sync_status')
    op.drop_column('recordings', 'checksum')
    op.drop_column('recordings', 'mime_type')
    op.drop_column('recordings', 'filesize_bytes')
    op.drop_column('recordings', 'stored_filename')
