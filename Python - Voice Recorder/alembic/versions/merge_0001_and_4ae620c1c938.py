"""Merge heads: 0001_create_recordings_table and 4ae620c1c938

Revision ID: merge_0001_and_4ae620c1c938
Revises: 4ae620c1c938, 0001_create_recordings_table
Create Date: 2025-10-06
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'merge_0001_and_4ae620c1c938'
down_revision = ('4ae620c1c938', '0001_create_recordings_table')
branch_labels = None
depends_on = None


def upgrade():
    # This is an empty merge migration to unify multiple heads created earlier.
    pass


def downgrade():
    # Downgrade not supported for merge-only revisions.
    pass
