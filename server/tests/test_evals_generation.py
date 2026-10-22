"""Phase 1 — automatic evaluation on every successful generation.

The contract this file exists to protect, in one sentence: **the
evaluator may fail, the generation may not.** Every other test here is
secondary to `test_scoring_failure_does_not_fail_the_generation`.

No network and no database: the pipeline services are mocked, which is
also the case most likely to produce nonsense inputs (a MagicMock where a
dict belongs), so the guards in ``evals.generation`` are exercised by
construction.
"""

import importlib
import time
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models.generation_job import GenerationJob
from app.evals import store
from app.evals.generation import build_generation_eval
from app.evals.router import register_eval_routes
from app.services.generation_job_service import GenerationJobService

JOB_MODULE = "app.services.generation_job_service"


def _brd_data() -> dict:
    return {
        "executive_summary": {"content": "A checkout redesign."},
        "project_overview": {
            "project_name": "Checkout Redesign",
            "description": "Reworking the storefront checkout.",
        },
        "business_objectives": {"objectives": ["Reduce abandonment."]},
        "scope": {"in_scope": ["Card payments."], "out_of_scope": ["Crypto."]},
        "stakeholders": {"stakeholders": [{"name": "Priya Raman"}]},
        "business_requirements": {"requirements": ["Accept card payments."]},
        "functional_requirements": {
            "requirements": [
                "Users must sign in with Google single sign-on.",
            ],
        },
        "non_functional_requirements": {
            "requirements": ["The checkout page must load in under two seconds."],
        },
        "assumptions_and_constraints": {
            "assumptions": ["The provider contract is renewed."],
            "constraints": ["Launch is limited to India."],
        },
        "risks_and_decisions": {
            "risks": ["A provider outage blocks checkout."],
            "decisions": ["Use the existing provider."],
        },
        "open_questions": {"questions": ["Do wallets ship in phase one?"]},
    }


def _knowledge_data() -> dict:
    return {
        "project_metadata": None,
        "stakeholders": [],
        "business_objectives": [],
        "functional_requirements": [
            {"description": "Users must sign in with Google single sign-on."},
        ],
        "non_functional_requirements": [
            {
                "category": "Performance",
                "description": "The checkout page must load in under two seconds.",
            },
        ],
        "assumptions": [],
        "constraints": [],
        "risks": [],
        "decisions": [],
        "out_of_scope": [],
        "open_questions": [],
    }


def _job() -> GenerationJob:
    job = GenerationJob(
        workspace_id=uuid4(),
        user_id=uuid4(),
    )
    job.id = uuid4()
    job.status = "running"
    job.phase = "generating_brd"
    job.error = None
    job.source_revision = 0
    job.updated_at = None

    return job


def _service(job: GenerationJob, *, has_new_sources: bool = False):
    service = GenerationJobService(MagicMock())

    service.db.get = MagicMock(return_value=job)
    service.standard_document_repository.has_unextracted_by_workspace_id = (
        MagicMock(return_value=has_new_sources)
    )

    return service


def _install_pipeline(
    monkeypatch,
    *,
    brd_data=None,
    knowledge_data=None,
    usage=None,
    has_new_sources=False,
):
    """Mock the three services the worker builds, and return the job."""
    module = importlib.import_module(JOB_MODULE)

    extraction_service = MagicMock()
    extraction_service.extract_workspace_documents.return_value = object()

    knowledge_service = MagicMock()
    knowledge_service.consolidate_project_knowledge.return_value = (
        SimpleNamespace(knowledge_data=knowledge_data)
    )

    brd_service = MagicMock()
    brd_service.generate_brd_for_user.return_value = SimpleNamespace(
        brd_data=brd_data,
    )
    brd_service.brd_generator = SimpleNamespace(last_usage=usage)

    monkeypatch.setattr(
        module,
        "DocumentExtractionService",
        lambda db: extraction_service,
    )
    monkeypatch.setattr(
        module,
        "ProjectKnowledgeService",
        lambda db: knowledge_service,
    )
    monkeypatch.setattr(module, "BRDService", lambda db: brd_service)

    job = _job()

    return job, _service(job, has_new_sources=has_new_sources)


@pytest.fixture
def records_dir(tmp_path, monkeypatch):
    """Point the store at a temporary directory and enable the hook."""
    monkeypatch.setattr(store, "default_directory", lambda: tmp_path)
    monkeypatch.setattr(settings, "eval_on_generation", True)
    monkeypatch.setattr(settings, "environment", "development")

    return tmp_path


# --------------------------------------------------------- the hook fires


def test_successful_generation_writes_a_record(monkeypatch, records_dir):
    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
        usage={
            "model": "gemini-2.5-flash",
            "prompt_tokens": 3125,
            "thought_tokens": 1491,
            "seconds": 13.9,
        },
    )

    service.execute_job(job.id)

    assert job.status == "succeeded"

    records = store.list_records()

    assert len(records) == 1

    record = records[0]

    assert record["job_id"] == str(job.id)
    assert record["workspace_id"] == str(job.workspace_id)
    assert record["usage"]["thought_tokens"] == 1491

    # Every metric ran, and the summary is derived from them rather than
    # computed a second way.
    assert set(record["metrics"]) == {
        "structure",
        "retention",
        "groundedness",
        "duplication",
    }
    assert record["summary"]["sections_present"] == 11
    assert record["summary"]["retention"] == 1.0
    assert record["summary"]["valid"] is True


def test_timings_are_recorded_per_phase(monkeypatch, records_dir):
    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
    )

    service.execute_job(job.id)

    timings = store.list_records()[0]["timings"]

    # No new sources here, so extraction legitimately did not run: the
    # phase is absent rather than recorded as 0.0.
    assert "processing_sources" not in timings
    assert set(timings) == {"preparing_knowledge", "generating_brd"}
    assert all(value >= 0 for value in timings.values())


def test_extraction_phase_is_recorded_when_it_runs(
    monkeypatch,
    records_dir,
):
    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
        has_new_sources=True,
    )

    service.execute_job(job.id)

    timings = store.list_records()[0]["timings"]

    assert "processing_sources" in timings


# ------------------------------------------------- the hook must not bite


def test_scoring_failure_does_not_fail_the_generation(
    monkeypatch,
    records_dir,
    caplog,
):
    """The one invariant: a broken evaluator must not touch the job."""
    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
    )

    module = importlib.import_module(JOB_MODULE)

    def explode(**kwargs):
        raise RuntimeError("evaluation is broken")

    monkeypatch.setattr(module, "build_generation_eval", explode)

    with caplog.at_level("WARNING", logger="brd-agent.generation"):
        service.execute_job(job.id)

    assert job.status == "succeeded"
    assert job.error is None
    assert "Evaluation record for job" in caplog.text
    assert store.list_records() == []


def test_production_writes_nothing(monkeypatch, records_dir):
    monkeypatch.setattr(settings, "environment", "production")

    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
    )

    service.execute_job(job.id)

    assert job.status == "succeeded"
    assert store.list_records() == []


def test_hook_can_be_switched_off(monkeypatch, records_dir):
    monkeypatch.setattr(settings, "eval_on_generation", False)

    job, service = _install_pipeline(
        monkeypatch,
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
    )

    service.execute_job(job.id)

    assert store.list_records() == []


def test_mocked_pipeline_does_not_produce_nonsense(monkeypatch, records_dir):
    """A MagicMock where a dict belongs must degrade, not crash."""
    job, service = _install_pipeline(monkeypatch)

    service.execute_job(job.id)

    records = store.list_records()

    assert job.status == "succeeded"
    assert len(records) == 1

    record = records[0]

    assert record["metrics"]["structure"]["valid"] is False
    assert record["metrics"]["retention"]["available"] is False
    assert record["usage"] is None


# ------------------------------------------------------------ the record


def test_record_omits_user_and_brd_copy():
    record = build_generation_eval(
        job_id=uuid4(),
        workspace_id=uuid4(),
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
        timings={"generating_brd": 13.9},
        usage={"model": "gemini-2.5-flash"},
    )

    # The BRD lives in the database; duplicating it here would double the
    # storage for no gain, and the user id is not needed to read a record.
    assert "brd_data" not in record
    assert "user_id" not in record
    assert record["summary"]["total_seconds"] == 13.9


def test_usage_must_be_a_real_dict():
    record = build_generation_eval(
        job_id=uuid4(),
        workspace_id=uuid4(),
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
        usage=MagicMock(),
    )

    assert record["usage"] is None


# ---------------------------------------------------------------- store


def test_save_record_includes_its_id(records_dir):
    record = build_generation_eval(
        job_id=uuid4(),
        workspace_id=uuid4(),
        brd_data=_brd_data(),
        knowledge_data=_knowledge_data(),
    )

    record_id = store.save_record(record, directory=records_dir)

    assert record_id is not None

    stored = store.load_record(record_id, directory=records_dir)

    assert stored["record_id"] == record_id


def test_prune_keeps_the_newest(records_dir):
    for index in range(55):
        (records_dir / f"20260101T0000{index:02d}000000-job{index}.json").write_text(
            "{}",
            encoding="utf-8",
        )

    removed = store.prune(directory=records_dir, keep=50)

    remaining = sorted(path.name for path in records_dir.glob("*.json"))

    assert removed == 5
    assert len(remaining) == 50
    assert remaining[0] == "20260101T000005000000-job5.json"
    assert remaining[-1] == "20260101T000054000000-job54.json"


def test_saving_prunes_automatically(records_dir):
    for _ in range(3):
        store.save_record(
            {"job_id": str(uuid4()), "summary": {}},
            directory=records_dir,
            keep=2,
        )

        # Timestamps are microsecond-resolution; without this two writes
        # can land in the same microsecond and overwrite each other.
        time.sleep(0.002)

    assert len(list(records_dir.glob("*.json"))) == 2


def test_record_id_validation_rejects_traversal():
    assert store.load_record("../../etc/passwd") is None
    assert store.is_valid_record_id("../etc/passwd") is False
    assert store.is_valid_record_id("20260101T000000000000-abc-123") is True


def test_unreadable_record_is_skipped_not_raised(records_dir):
    (records_dir / "20260101T000000000000-broken.json").write_text(
        "{not json",
        encoding="utf-8",
    )
    (records_dir / "20260101T000001000000-good.json").write_text(
        '{"job_id": "good"}',
        encoding="utf-8",
    )

    records = store.list_records()

    assert [record["job_id"] for record in records] == ["good"]


# --------------------------------------------------------------- routes


def _eval_paths(app) -> list[str]:
    """Eval paths from the OpenAPI schema.

    ``app.routes`` is not usable here: this FastAPI version wraps included
    routers in a container object with no ``path``, so counting it reports
    zero regardless. OpenAPI is also what actually matters — a route that
    is not in the schema is not reachable.
    """
    return sorted(
        path for path in app.openapi().get("paths", {}) if path.startswith("/evals")
    )


def test_routes_are_absent_in_production():
    from fastapi import FastAPI

    app = FastAPI()

    mounted = register_eval_routes(
        app,
        SimpleNamespace(environment="production", eval_enabled=True),
    )

    assert mounted is False
    assert _eval_paths(app) == []


def test_routes_can_be_disabled_in_development():
    from fastapi import FastAPI

    app = FastAPI()

    mounted = register_eval_routes(
        app,
        SimpleNamespace(environment="development", eval_enabled=False),
    )

    assert mounted is False
    assert _eval_paths(app) == []


def test_routes_are_mounted_in_development():
    from fastapi import FastAPI

    app = FastAPI()

    mounted = register_eval_routes(
        app,
        SimpleNamespace(environment="development", eval_enabled=True),
    )

    assert mounted is True
    assert _eval_paths(app) == [
        "/evals/generations",
        "/evals/generations/{record_id}",
    ]


def _client():
    from app.auth.current_user import get_current_db_user
    from app.main import app

    app.dependency_overrides[get_current_db_user] = lambda: SimpleNamespace(
        id=uuid4(),
    )

    return app, TestClient(app)


def test_list_endpoint_returns_summaries_newest_first(records_dir):
    for _ in range(2):
        store.save_record(
            build_generation_eval(
                job_id=uuid4(),
                workspace_id=uuid4(),
                brd_data=_brd_data(),
                knowledge_data=_knowledge_data(),
            ),
            directory=records_dir,
        )

        time.sleep(0.002)

    app, client = _client()

    try:
        response = client.get("/evals/generations")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 2

    first, second = payload["records"]

    assert first["recorded_at"] >= second["recorded_at"]
    # Summaries only — the listing must not ship every full record.
    assert "metrics" not in first
    assert "retention" in first["summary"]


def test_detail_endpoint_returns_the_full_record(records_dir):
    record_id = store.save_record(
        build_generation_eval(
            job_id=uuid4(),
            workspace_id=uuid4(),
            brd_data=_brd_data(),
            knowledge_data=_knowledge_data(),
        ),
        directory=records_dir,
    )

    app, client = _client()

    try:
        response = client.get(f"/evals/generations/{record_id}")
        missing = client.get("/evals/generations/does-not-exist")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "metrics" in response.json()

    assert missing.status_code == 404


# ------------------------------------------------------- test bootstrap


def test_settings_load_without_a_dotenv_file():
    """The suite must not depend on a developer's local .env."""
    from app.core.config import Settings

    assert Settings().database_url
