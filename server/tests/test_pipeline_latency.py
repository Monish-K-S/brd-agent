"""Batch E — pipeline latency guardrails.

Four contract-safe changes, each with the regression it must not
reintroduce:

- **P-7** API responses are gzipped (BRD payload is the large one).
- **P-4** the status path reads a BRD summary (no ``brd_data``), so the
  2s poll during a generation stops shipping the whole document.
- **P-5** ``BRDService`` builds its Gemini generator lazily, so the
  read paths (status / exports / edit) neither allocate a genai client
  nor require ``GEMINI_API_KEY``.
- **P-3** the Sarvam extraction ceiling is configurable instead of a
  hardcoded 60 x 2s, and a job is no longer slept on after its final
  poll.

No DB and no network here — the repositories use a capturing session
(the M-3 pattern) and the Sarvam client is faked.
"""

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

import app.db.models  # noqa: F401 — registers every mapper
from app.core.config import Settings, settings
from app.repositories.brd_repository import BRDRepository


class _FakeResult:
    _attributes = {}

    def scalars(self):
        return self

    def unique(self):
        return self

    def first(self):
        return None

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


# ---------------------------------------------------------------- P-7


def test_gzip_middleware_is_installed():
    from fastapi.middleware.gzip import GZipMiddleware

    from app.main import app

    classes = [
        middleware.cls for middleware in app.user_middleware
    ]

    assert GZipMiddleware in classes


def test_gzip_threshold_lets_small_payloads_through_uncompressed():
    from fastapi.middleware.gzip import GZipMiddleware

    from app.main import app

    gzip_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is GZipMiddleware
    )

    assert gzip_middleware.kwargs.get("minimum_size") == 1000


def test_gzip_is_the_innermost_middleware():
    """It must sit closest to the routes.

    The BaseHTTPMiddleware layers above re-stream bodies; if gzip wrapped
    *them* instead, every response would arrive as a stream and the
    minimum_size gate would never apply (verified: a 43-byte /health body
    was compressed).
    """
    from fastapi.middleware.gzip import GZipMiddleware

    from app.main import app

    assert app.user_middleware[-1].cls is GZipMiddleware


def test_gzip_excludes_export_content_types():
    from fastapi.middleware.gzip import GZipMiddleware

    from app.main import app

    gzip_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls is GZipMiddleware
    )

    excluded = gzip_middleware.kwargs["exclude_content_types"]

    assert "application/pdf" in excluded
    assert any(
        "wordprocessingml" in content_type
        for content_type in excluded
    )


def test_gzip_compresses_large_json_only():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    plain = client.get(
        "/openapi.json",
        headers={"Accept-Encoding": "identity"},
    )

    with client.stream(
        "GET",
        "/openapi.json",
        headers={"Accept-Encoding": "gzip"},
    ) as response:
        compressed = b"".join(response.iter_raw())

        assert response.headers.get("content-encoding") == "gzip"

    with client.stream(
        "GET",
        "/health",
        headers={"Accept-Encoding": "gzip"},
    ) as response:
        small = b"".join(response.iter_raw())

        assert response.headers.get("content-encoding") is None
        assert response.headers.get("content-length") == str(len(small))

    # A large JSON payload must actually shrink on the wire.
    assert len(compressed) < len(plain.content)


# ---------------------------------------------------------------- P-4


def test_status_query_defers_brd_data():
    session = _CapturingSession()
    repository = BRDRepository(session)

    repository.get_summary_by_workspace_id(uuid4())

    assert len(session.statements) == 1
    assert ".brd_data" not in _select_clause(session.statements[0])


def test_full_brd_query_still_selects_data():
    session = _CapturingSession()
    repository = BRDRepository(session)

    repository.get_by_workspace_id(uuid4())

    assert len(session.statements) == 1
    assert ".brd_data" in _select_clause(session.statements[0])


def test_status_service_uses_the_summary_projection():
    from app.services.brd_service import BRDService

    source = inspect.getsource(BRDService.get_brd_status_for_user)

    assert "get_summary_by_workspace_id" in source
    assert "get_by_workspace_id" not in source


# ---------------------------------------------------------------- P-5


def test_brd_service_builds_the_generator_lazily(monkeypatch):
    from app.services import brd_service as brd_service_module

    built = []

    class FakeGenerator:
        def __init__(self, schema_path):
            built.append(schema_path)

    monkeypatch.setattr(
        brd_service_module,
        "GeminiBRDGenerator",
        FakeGenerator,
    )

    service = brd_service_module.BRDService(MagicMock())

    # Construction must not allocate a genai client (status/export paths).
    assert built == []

    first = service.brd_generator
    second = service.brd_generator

    assert first is second
    assert len(built) == 1


def test_lazy_generator_does_not_need_gemini_key_to_construct(monkeypatch):
    from app.services import brd_service as brd_service_module

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Would raise RuntimeError("GEMINI_API_KEY is not set") if eager.
    service = brd_service_module.BRDService(MagicMock())

    assert service._brd_generator is None


# ---------------------------------------------------------------- P-3


class _FakeDocAI:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def get_status(self, job_id):
        self.calls += 1

        if self.statuses:
            return SimpleNamespace(status=self.statuses.pop(0))

        return SimpleNamespace(status="processing")


def _make_extractor(monkeypatch, statuses, timeout_seconds=None):
    from app.ai.extractors.sarvam_extractor import SarvamExtractor

    monkeypatch.setenv("SARVAM_API_KEY", "test-key")

    fake_client = SimpleNamespace(doc_ai=_FakeDocAI(statuses))

    monkeypatch.setattr(
        "app.ai.extractors.sarvam_extractor.SarvamAI",
        lambda **kwargs: fake_client,
    )

    sleeps = []

    monkeypatch.setattr(
        "app.ai.extractors.sarvam_extractor.time.sleep",
        sleeps.append,
    )

    extractor = SarvamExtractor(
        schema_path="unused.json",
        timeout_seconds=timeout_seconds,
    )

    return extractor, fake_client.doc_ai, sleeps


def test_sarvam_default_ceiling_comes_from_settings(monkeypatch):
    extractor, _, _ = _make_extractor(monkeypatch, statuses=[])

    assert (
        Settings.model_fields["sarvam_timeout_seconds"].default
        == 180
    )
    assert extractor.timeout_seconds == settings.sarvam_timeout_seconds


def test_sarvam_poll_budget_follows_the_timeout(monkeypatch):
    extractor, _, _ = _make_extractor(
        monkeypatch,
        statuses=[],
        timeout_seconds=6,
    )

    assert extractor.max_attempts == 3

    extractor, _, _ = _make_extractor(
        monkeypatch,
        statuses=[],
        timeout_seconds=7,
    )

    # Ceil, so a partial interval still gets its poll.
    assert extractor.max_attempts == 4


def test_sarvam_times_out_at_the_configured_ceiling(monkeypatch):
    extractor, doc_ai, sleeps = _make_extractor(
        monkeypatch,
        statuses=[],
        timeout_seconds=6,
    )

    with pytest.raises(TimeoutError, match="timed out"):
        extractor._wait_for_completion(job_id="job-1")

    assert doc_ai.calls == 3
    assert len(sleeps) == 2  # no sleep after the final poll


def test_sarvam_returns_as_soon_as_the_job_completes(monkeypatch):
    extractor, doc_ai, sleeps = _make_extractor(
        monkeypatch,
        statuses=["processing", "completed"],
        timeout_seconds=180,
    )

    extractor._wait_for_completion(job_id="job-2")

    assert doc_ai.calls == 2
    assert sleeps == [2]


def test_sarvam_failed_status_still_raises(monkeypatch):
    extractor, doc_ai, _ = _make_extractor(
        monkeypatch,
        statuses=["failed"],
        timeout_seconds=6,
    )

    with pytest.raises(RuntimeError, match="Sarvam extraction failed"):
        extractor._wait_for_completion(job_id="job-3")

    assert doc_ai.calls == 1


def test_sarvam_cancelled_status_still_raises(monkeypatch):
    extractor, _, _ = _make_extractor(
        monkeypatch,
        statuses=["cancelled"],
        timeout_seconds=6,
    )

    with pytest.raises(RuntimeError, match="Sarvam extraction failed"):
        extractor._wait_for_completion(job_id="job-4")


# ------------------------------------------------- E-0 observability


def test_phase_timing_is_logged_at_info(caplog):
    import logging
    import time

    from app.services.generation_job_service import (
        GenerationJobService,
        PHASE_GENERATING_BRD,
    )

    service = GenerationJobService(MagicMock())

    with caplog.at_level(
        logging.INFO,
        logger="brd-agent.generation",
    ):
        service._log_phase(
            uuid4(),
            PHASE_GENERATING_BRD,
            time.perf_counter(),
        )

    assert "phase=generating_brd took" in caplog.text
