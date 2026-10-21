"""add workspace-scoped indexes

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-10-21

Postgres does not index foreign keys automatically, and every hot query
in this app filters on a workspace:

- ``standard_documents``  -- document listing, duplicate-upload checks,
  ``has_unextracted_by_workspace_id`` on each generation start.
- ``document_extractions`` -- consolidation reads all of them per run.
- ``document_extraction_documents.standard_document_id`` -- the ORM
  cascade issues ``WHERE standard_document_id = ?`` on document delete,
  which the existing composite unique cannot serve because it leads with
  ``document_extraction_id``.

Deliberately **not** included, despite the original P-8 finding claiming
five tables needed this (corrected 2026-10-21 against live ``pg_indexes``):

- ``brds`` and ``project_knowledge`` already carry a btree on
  ``workspace_id`` -- their ``unique=True`` column constraint creates
  ``brds_workspace_id_key`` / ``project_knowledge_workspace_id_key``.
- ``workspaces.user_id`` is the leading column of
  ``uq_workspaces_user_lower_name`` (corrected 2026-10-19 during R-1).
- ``generation_jobs`` already has both ``ix_generation_jobs_workspace_id``
  and the partial unique index from ``b8c9d0e1f2a3``.

Adding a redundant index costs write throughput and disk for nothing, so
do not "complete the set" later without re-checking ``pg_indexes`` first.

Plain ``CREATE INDEX`` (not ``CONCURRENTLY``) is intentional: these tables
are tiny, and ``CONCURRENTLY`` cannot run inside Alembic's transaction.

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEXES = (
    (
        "ix_standard_documents_workspace_id",
        "standard_documents",
        "workspace_id",
    ),
    (
        "ix_document_extractions_workspace_id",
        "document_extractions",
        "workspace_id",
    ),
    (
        "ix_document_extraction_documents_standard_document_id",
        "document_extraction_documents",
        "standard_document_id",
    ),
)


def upgrade() -> None:
    """Create the three missing workspace-scoped indexes."""

    for index_name, table_name, column_name in _INDEXES:
        op.create_index(
            index_name,
            table_name,
            [column_name],
        )


def downgrade() -> None:
    """Drop exactly the indexes created above (no data change)."""

    for index_name, table_name, column_name in reversed(_INDEXES):
        op.drop_index(
            index_name,
            table_name=table_name,
        )
