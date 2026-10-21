"""Workspace-scoped indexes (P-8).

Postgres does not index foreign keys, and every hot query in this app
filters on a workspace. These tests pin two things that are otherwise
invisible until production gets slow:

1. The indexes the migration creates are still declared in model
   metadata under the *same names*. If a column is renamed, or an
   ``index=True`` is dropped, autogenerate would try to create a second
   index (or nothing at all) while the migration quietly keeps the old
   one — the DB and the models drift apart with no failure anywhere.
2. We do not re-add indexes that already exist. ``brds`` and
   ``project_knowledge`` get a btree on ``workspace_id`` for free from
   their ``unique=True`` column constraint, and ``workspaces.user_id``
   is the leading column of ``uq_workspaces_user_lower_name``. A
   duplicate index costs write throughput and disk for no read gain,
   so the "complete the set" instinct is explicitly guarded against.
"""

import pytest

from app.db.models.document_extraction import DocumentExtraction
from app.db.models.document_extraction_document import (
    DocumentExtractionDocument,
)
from app.db.models.standard_document import StandardDocument


# (model, index name, column name) — must match migration c1d2e3f4a5b6.
EXPECTED_INDEXES = [
    (
        StandardDocument,
        "ix_standard_documents_workspace_id",
        "workspace_id",
    ),
    (
        DocumentExtraction,
        "ix_document_extractions_workspace_id",
        "workspace_id",
    ),
    (
        DocumentExtractionDocument,
        "ix_document_extraction_documents_standard_document_id",
        "standard_document_id",
    ),
]


def _indexed_columns(model) -> dict[str, list[str]]:
    """Map index name -> column names declared in model metadata."""

    return {
        index.name: [column.name for column in index.columns]
        for index in model.__table__.indexes
    }


@pytest.mark.parametrize(
    ("model", "index_name", "column_name"),
    EXPECTED_INDEXES,
)
def test_workspace_scope_is_indexed(model, index_name, column_name):
    indexed = _indexed_columns(model)

    assert index_name in indexed, (
        f"{model.__tablename__} is missing {index_name}; the migration "
        "creates it but the model no longer declares it, so the two "
        "have drifted apart."
    )
    assert indexed[index_name] == [column_name]


def test_the_composite_unique_does_not_cover_document_lookups():
    # The cascade delete filters on standard_document_id alone; the
    # composite unique leads with document_extraction_id and therefore
    # cannot serve it. This is why the third index exists at all.
    unique_columns = [
        [column.name for column in constraint.columns]
        for constraint in (
            DocumentExtractionDocument.__table__.constraints
        )
        if constraint.__class__.__name__ == "UniqueConstraint"
    ]

    assert ["document_extraction_id", "standard_document_id"] in (
        unique_columns
    )
    assert ["standard_document_id"] not in unique_columns


@pytest.mark.parametrize(
    "table_name",
    ["brds", "project_knowledge"],
)
def test_no_redundant_index_on_already_unique_columns(table_name):
    # Both tables declare workspace_id with unique=True, which Postgres
    # backs with a btree named <table>_workspace_id_key. Adding an
    # explicit index would duplicate it.
    from app.db.base import Base

    table = Base.metadata.tables[table_name]

    redundant = {
        index.name: [column.name for column in index.columns]
        for index in table.indexes
    }

    assert "workspace_id" not in [
        column
        for columns in redundant.values()
        for column in columns
    ], (
        f"{table_name} already has a unique btree on workspace_id; "
        "an extra index is pure write overhead."
    )
