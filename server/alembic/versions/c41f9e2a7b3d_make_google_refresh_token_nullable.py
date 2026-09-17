"""make google refresh token nullable

Revision ID: c41f9e2a7b3d
Revises: a79337b3268f
Create Date: 2026-09-18 10:00:00.000000

Google omits refresh_token on re-consent without prompt=consent.
A NOT NULL column turns that into an IntegrityError (500) on connect.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41f9e2a7b3d'
down_revision: Union[str, Sequence[str], None] = 'a79337b3268f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "google_connections",
        "refresh_token",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    # Remove rows that would violate NOT NULL before re-imposing it.
    op.execute(
        "DELETE FROM google_connections WHERE refresh_token IS NULL"
    )
    op.alter_column(
        "google_connections",
        "refresh_token",
        existing_type=sa.String(),
        nullable=False,
    )
