"""M-3: document list must not ship full content.

GET /workspaces/{id}/documents and POST .../upload respond with
StandardDocumentSummary (content omitted; rows carry up to 500k
extracted chars). The per-document GET keeps the full
StandardDocumentResponse, and the repository summary query must
defer the content column at the SQL level.
"""

from uuid import uuid4

import app.db.models.google_connection  # noqa: F401 — registers mapper
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.api.routes.standard_document import router
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.schemas.standard_document import (
    StandardDocumentResponse,
    StandardDocumentSummary,
)


def test_summary_schema_omits_content():
    assert "content" not in StandardDocumentSummary.model_fields
    assert "content" in StandardDocumentResponse.model_fields


def test_summary_keeps_list_surface_fields():
    expected = {
        "id",
        "workspace_id",
        "source_type",
        "title",
        "author",
        "source_created_at",
        "participants",
        "metadata",
        "created_at",
        "updated_at",
    }

    assert expected == set(StandardDocumentSummary.model_fields)


def test_list_and_upload_routes_use_summary_model():
    response_models = {
        (route.path, tuple(sorted(route.methods))): route.response_model
        for route in router.routes
    }

    assert response_models[
        ("/workspaces/{workspace_id}/documents", ("GET",))
    ] == list[StandardDocumentSummary]
    assert response_models[
        ("/workspaces/{workspace_id}/documents/upload", ("POST",))
    ] == list[StandardDocumentSummary]


def test_per_document_route_keeps_full_model():
    for route in router.routes:
        if route.path == (
            "/workspaces/{workspace_id}/documents/{document_id}"
        ) and "GET" in route.methods:
            assert route.response_model == StandardDocumentResponse

            return

    raise AssertionError("per-document GET route not found")


class _FakeResult:
    _attributes = {}

    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return []


class _CapturingSession(Session):
    def __init__(self):
        super().__init__()

        self.statements = []

    def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)

        return _FakeResult()


def _select_clause(statement):
    return str(
        statement.compile(dialect=postgresql.dialect())
    ).split("FROM")[0]


def test_summary_query_defers_content_column():
    session = _CapturingSession()
    repository = StandardDocumentRepository(session)

    repository.get_summaries_by_workspace_id(uuid4())

    assert len(session.statements) == 1
    assert ".content" not in _select_clause(session.statements[0])


def test_full_query_still_selects_content():
    session = _CapturingSession()
    repository = StandardDocumentRepository(session)

    repository.get_all_by_workspace_id(uuid4())

    assert len(session.statements) == 1
    assert ".content" in _select_clause(session.statements[0])
