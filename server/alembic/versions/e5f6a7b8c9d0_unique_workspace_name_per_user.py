"""unique workspace name per user (case-insensitive)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-26 00:00:00.000000

Hard-blocks duplicate workspace names per user: functional unique
index on (user_id, lower(name)). Names are stripped at the API
boundary, so lower() covers Test/test/" Test " variants.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'uq_workspaces_user_lower_name',
        'workspaces',
        [sa.text('user_id'), sa.text('lower(name)')],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_workspaces_user_lower_name', table_name='workspaces')
