"""add source revision to brds

Revision ID: 5e297e812d8f
Revises: 30cc5d0eee49
Create Date: 2026-09-13 18:18:33.766440

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e297e812d8f"
down_revision: Union[str, Sequence[str], None] = "30cc5d0eee49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "brds",
        sa.Column(
            "source_revision",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "brds",
        "source_revision",
    )
