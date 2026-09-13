"""add source revision to workspaces

Revision ID: 30cc5d0eee49
Revises: ec48f2ca3e73
Create Date: 2026-09-13 18:09:55.426376

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "30cc5d0eee49"
down_revision: Union[str, Sequence[str], None] = "ec48f2ca3e73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspaces",
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
        "workspaces",
        "source_revision",
    )
