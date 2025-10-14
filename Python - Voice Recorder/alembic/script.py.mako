"""Generic Alembic script template (minimal)

This file is intentionally small; Alembic's `revision --autogenerate` will use
this template to render migration scripts.
"""
<%text>
Revision ID: ${up_revision}
Revises: ${down_revision | none}
Create Date: ${create_date}
</%text>

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
