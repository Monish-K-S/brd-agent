"""one active generation job per workspace

Revision ID: b8c9d0e1f2a3
Revises: f7a1c9e4b206
Create Date: 2026-10-11

Two concurrent POST /brd/generate can both pass the application-level
active-job check and enqueue parallel pipelines (last save_brd wins,
user edits silently lost). A partial unique index enforces a single
queued/running job per workspace at the database level; the service
treats the resulting IntegrityError as "adopt the existing job".

The upgrade first terminalizes pre-existing duplicate actives (all but
the latest per workspace) so index creation cannot fail on ghost rows
orphaned by earlier restarts. The downgrade only drops the index.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'f7a1c9e4b206'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fail superseded duplicate actives, then enforce singularity."""

    # Keep only the latest active job per workspace; older ones are
    # ghosts of the create-vs-create race (or of a restart) and must
    # never block the index.
    op.execute(
        """
        UPDATE public.generation_jobs j
        SET status = 'failed',
            error = 'Superseded by a newer generation run'
        WHERE j.status IN ('queued', 'running')
          AND EXISTS (
              SELECT 1
              FROM public.generation_jobs newer
              WHERE newer.workspace_id = j.workspace_id
                AND newer.status IN ('queued', 'running')
                AND (
                    newer.created_at > j.created_at
                    OR (
                        newer.created_at = j.created_at
                        AND newer.id > j.id
                    )
                )
          )
        """
    )

    op.create_index(
        "uq_generation_jobs_one_active_per_workspace",
        "generation_jobs",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    """Drop the singularity index (failed superseded rows stay failed)."""

    op.drop_index(
        "uq_generation_jobs_one_active_per_workspace",
        table_name="generation_jobs",
    )
