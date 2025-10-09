"""merge heads

Revision ID: merge_0001_and_4ae620c1c938
Revises: 4ae620c1c938, 0001_create_recordings_and_jobs
Create Date: 2025-10-09 13:25:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'merge_0001_and_4ae620c1c938'
down_revision = ('4ae620c1c938', '0001_create_recordings_and_jobs')
branch_labels = None
depends_on = None


def upgrade():
    # Merge-only revision: no DB schema changes, used to unify history heads
    pass


def downgrade():
    # No-op downgrade for merge revision
    pass
