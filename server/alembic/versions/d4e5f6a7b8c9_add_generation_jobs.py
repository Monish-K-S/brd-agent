"""add generation jobs

Revision ID: d4e5f6a7b8c9
Revises: c41f9e2a7b3d
Create Date: 2026-09-26 00:00:00.000000

Async BRD pipeline runs (extract → consolidate → generate), created by
POST /brd/generate and executed by an in-process background task.
Polled via GET /brd/status (active_job). History pruned to latest 3
per workspace by application code.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c41f9e2a7b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('generation_jobs',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='queued', nullable=False),
    sa.Column('phase', sa.String(length=32), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('source_revision', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generation_jobs_workspace_id', 'generation_jobs', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_generation_jobs_workspace_id', table_name='generation_jobs')
    op.drop_table('generation_jobs')
