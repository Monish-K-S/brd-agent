"""enable row level security

Revision ID: a79337b3268f
Revises: b23bf7c1a59c
Create Date: 2026-09-17 18:22:38.440556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a79337b3268f'
down_revision: Union[str, Sequence[str], None] = 'b23bf7c1a59c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable RLS and create row ownership policies."""

    # Enable RLS
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.brds ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.standard_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.document_extractions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.project_knowledge ENABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE public.document_extraction_documents "
        "ENABLE ROW LEVEL SECURITY"
    )
    op.execute("ALTER TABLE public.google_connections ENABLE ROW LEVEL SECURITY")

    # users: users can access only their own row
    op.execute(
        """
        CREATE POLICY users_select_own
        ON public.users
        FOR SELECT
        TO authenticated
        USING (id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY users_update_own
        ON public.users
        FOR UPDATE
        TO authenticated
        USING (id = auth.uid())
        WITH CHECK (id = auth.uid())
        """
    )

    # workspaces: users can access only their own workspaces
    op.execute(
        """
        CREATE POLICY workspaces_select_own
        ON public.workspaces
        FOR SELECT
        TO authenticated
        USING (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY workspaces_insert_own
        ON public.workspaces
        FOR INSERT
        TO authenticated
        WITH CHECK (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY workspaces_update_own
        ON public.workspaces
        FOR UPDATE
        TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
        """
    )

    op.execute(
        """
        CREATE POLICY workspaces_delete_own
        ON public.workspaces
        FOR DELETE
        TO authenticated
        USING (user_id = auth.uid())
        """
    )

    # brds: access through workspace ownership
    op.execute(
        """
        CREATE POLICY brds_select_own
        ON public.brds
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = brds.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY brds_insert_own
        ON public.brds
        FOR INSERT
        TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = brds.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY brds_update_own
        ON public.brds
        FOR UPDATE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = brds.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = brds.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY brds_delete_own
        ON public.brds
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = brds.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    # standard_documents: access through workspace ownership
    op.execute(
        """
        CREATE POLICY standard_documents_select_own
        ON public.standard_documents
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = standard_documents.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY standard_documents_insert_own
        ON public.standard_documents
        FOR INSERT
        TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = standard_documents.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY standard_documents_update_own
        ON public.standard_documents
        FOR UPDATE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = standard_documents.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = standard_documents.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY standard_documents_delete_own
        ON public.standard_documents
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = standard_documents.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    # document_extractions: access through workspace ownership
    op.execute(
        """
        CREATE POLICY document_extractions_select_own
        ON public.document_extractions
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = document_extractions.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_extractions_insert_own
        ON public.document_extractions
        FOR INSERT
        TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = document_extractions.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_extractions_update_own
        ON public.document_extractions
        FOR UPDATE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = document_extractions.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = document_extractions.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_extractions_delete_own
        ON public.document_extractions
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = document_extractions.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    # project_knowledge: access through workspace ownership
    op.execute(
        """
        CREATE POLICY project_knowledge_select_own
        ON public.project_knowledge
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = project_knowledge.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY project_knowledge_insert_own
        ON public.project_knowledge
        FOR INSERT
        TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = project_knowledge.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY project_knowledge_update_own
        ON public.project_knowledge
        FOR UPDATE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = project_knowledge.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = project_knowledge.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY project_knowledge_delete_own
        ON public.project_knowledge
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.workspaces AS w
                WHERE w.id = project_knowledge.workspace_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    # document_extraction_documents:
    # both referenced records must belong to the user's workspace
    op.execute(
        """
        CREATE POLICY document_extraction_documents_select_own
        ON public.document_extraction_documents
        FOR SELECT
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.document_extractions AS de
                JOIN public.workspaces AS w
                    ON w.id = de.workspace_id
                JOIN public.standard_documents AS sd
                    ON sd.workspace_id = de.workspace_id
                WHERE de.id = document_extraction_documents.document_extraction_id
                  AND sd.id = document_extraction_documents.standard_document_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_extraction_documents_insert_own
        ON public.document_extraction_documents
        FOR INSERT
        TO authenticated
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.document_extractions AS de
                JOIN public.workspaces AS w
                    ON w.id = de.workspace_id
                JOIN public.standard_documents AS sd
                    ON sd.workspace_id = de.workspace_id
                WHERE de.id = document_extraction_documents.document_extraction_id
                  AND sd.id = document_extraction_documents.standard_document_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_extraction_documents_delete_own
        ON public.document_extraction_documents
        FOR DELETE
        TO authenticated
        USING (
            EXISTS (
                SELECT 1
                FROM public.document_extractions AS de
                JOIN public.workspaces AS w
                    ON w.id = de.workspace_id
                JOIN public.standard_documents AS sd
                    ON sd.workspace_id = de.workspace_id
                WHERE de.id = document_extraction_documents.document_extraction_id
                  AND sd.id = document_extraction_documents.standard_document_id
                  AND w.user_id = auth.uid()
            )
        )
        """
    )

    # google_connections:
    # RLS is enabled intentionally, but no authenticated policies are
    # created because OAuth tokens must remain backend-only.


def downgrade() -> None:
    """Remove RLS policies and disable RLS."""

    # document_extraction_documents
    op.execute(
        "DROP POLICY IF EXISTS document_extraction_documents_delete_own "
        "ON public.document_extraction_documents"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extraction_documents_insert_own "
        "ON public.document_extraction_documents"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extraction_documents_select_own "
        "ON public.document_extraction_documents"
    )

    # project_knowledge
    op.execute(
        "DROP POLICY IF EXISTS project_knowledge_delete_own "
        "ON public.project_knowledge"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_knowledge_update_own "
        "ON public.project_knowledge"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_knowledge_insert_own "
        "ON public.project_knowledge"
    )
    op.execute(
        "DROP POLICY IF EXISTS project_knowledge_select_own "
        "ON public.project_knowledge"
    )

    # document_extractions
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_delete_own "
        "ON public.document_extractions"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_update_own "
        "ON public.document_extractions"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_insert_own "
        "ON public.document_extractions"
    )
    op.execute(
        "DROP POLICY IF EXISTS document_extractions_select_own "
        "ON public.document_extractions"
    )

    # standard_documents
    op.execute(
        "DROP POLICY IF EXISTS standard_documents_delete_own "
        "ON public.standard_documents"
    )
    op.execute(
        "DROP POLICY IF EXISTS standard_documents_update_own "
        "ON public.standard_documents"
    )
    op.execute(
        "DROP POLICY IF EXISTS standard_documents_insert_own "
        "ON public.standard_documents"
    )
    op.execute(
        "DROP POLICY IF EXISTS standard_documents_select_own "
        "ON public.standard_documents"
    )

    # brds
    op.execute(
        "DROP POLICY IF EXISTS brds_delete_own ON public.brds"
    )
    op.execute(
        "DROP POLICY IF EXISTS brds_update_own ON public.brds"
    )
    op.execute(
        "DROP POLICY IF EXISTS brds_insert_own ON public.brds"
    )
    op.execute(
        "DROP POLICY IF EXISTS brds_select_own ON public.brds"
    )

    # workspaces
    op.execute(
        "DROP POLICY IF EXISTS workspaces_delete_own ON public.workspaces"
    )
    op.execute(
        "DROP POLICY IF EXISTS workspaces_update_own ON public.workspaces"
    )
    op.execute(
        "DROP POLICY IF EXISTS workspaces_insert_own ON public.workspaces"
    )
    op.execute(
        "DROP POLICY IF EXISTS workspaces_select_own ON public.workspaces"
    )

    # users
    op.execute(
        "DROP POLICY IF EXISTS users_update_own ON public.users"
    )
    op.execute(
        "DROP POLICY IF EXISTS users_select_own ON public.users"
    )

    # Disable RLS
    op.execute("ALTER TABLE public.google_connections DISABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE public.document_extraction_documents "
        "DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.project_knowledge DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.document_extractions DISABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.standard_documents DISABLE ROW LEVEL SECURITY"
    )
    op.execute("ALTER TABLE public.brds DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.workspaces DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.users DISABLE ROW LEVEL SECURITY")
