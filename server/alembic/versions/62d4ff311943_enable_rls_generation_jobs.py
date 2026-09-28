"""enable row level security on generation_jobs

Revision ID: 62d4ff311943
Revises: e5f6a7b8c9d0
Create Date: 2026-09-28

Follows the convention from a79337b3268f_enable_row_level_security:
generation_jobs carries its own user_id column, so the simple
workspaces-style (user_id = auth.uid()) policies apply. All four
operations are needed: the backend inserts jobs, selects them during
status polling, updates phase/status in the background task, and
deletes during prune-to-latest-3.

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '62d4ff311943'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable RLS and create row ownership policies."""

    op.execute(
        "ALTER TABLE public.generation_jobs ENABLE ROW LEVEL SECURITY"
    )

    op.execute(
        """
        CREATE POLICY generation_jobs_select_own
        ON public.generation_jobs
        FOR SELECT
        TO authenticated
        USING (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY generation_jobs_insert_own
        ON public.generation_jobs
        FOR INSERT
        TO authenticated
        WITH CHECK (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY generation_jobs_update_own
        ON public.generation_jobs
        FOR UPDATE
        TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY generation_jobs_delete_own
        ON public.generation_jobs
        FOR DELETE
        TO authenticated
        USING (user_id = auth.uid())
        """
    )


def downgrade() -> None:
    """Remove RLS policies and disable RLS."""

    op.execute(
        "DROP POLICY IF EXISTS generation_jobs_delete_own "
        "ON public.generation_jobs"
    )
    op.execute(
        "DROP POLICY IF EXISTS generation_jobs_update_own "
        "ON public.generation_jobs"
    )
    op.execute(
        "DROP POLICY IF EXISTS generation_jobs_insert_own "
        "ON public.generation_jobs"
    )
    op.execute(
        "DROP POLICY IF EXISTS generation_jobs_select_own "
        "ON public.generation_jobs"
    )

    op.execute(
        "ALTER TABLE public.generation_jobs DISABLE ROW LEVEL SECURITY"
    )
