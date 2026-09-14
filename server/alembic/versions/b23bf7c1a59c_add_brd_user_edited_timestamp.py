"""add brd user edited timestamp

Revision ID: b23bf7c1a59c
Revises: 055920fe1d1e
Create Date: 2026-09-14 17:23:02.661808

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b23bf7c1a59c"
down_revision: Union[str, Sequence[str], None] = "055920fe1d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "brds",
        sa.Column(
            "user_edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "brds",
        "user_edited_at",
    )
