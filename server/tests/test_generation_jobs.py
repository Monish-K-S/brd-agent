"""Generation job lifecycle (Phase 2b).

Covers the async BRD pipeline without a database: schema backward
compatibility (old 5-field status payloads still parse), the
server-side concurrent guard, prune-to-latest-3, and the unified
worker pipeline with phase transitions — all with mocked sessions.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

import app.db.models.google_connection  # noqa: F401 — registers mapper
from app.db.models.generation_job import GenerationJob
from app.services.generation_job_service import (
    GenerationJobService,
    MAX_JOBS_PER_WORKSPACE,
    STALE_JOB_MESSAGE,
)


def make_job(**overrides):
    values = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "user_id": uuid4(),
        "status": "queued",
        "phase": None,
        "error": None,
        "source_revision": 0,
        "updated_at": None,
    }
    values.update(overrides)

    job = GenerationJob(
        workspace_id=values["workspace_id"],
        user_id=values["user_id"],
    )
    job.id = values["id"]
    job.status = values["status"]
    job.phase = values["phase"]
    job.error = values["error"]
    job.source_revision = values["source_revision"]
    job.updated_at = values["updated_at"]

    return job


def make_service():
    return GenerationJobService(MagicMock())


def test_status_response_backward_compat():
    from app.schemas.brd import BRDStatusResponse

    status = BRDStatusResponse(
        has_brd=True,
        has_sources=True,
        has_new_sources=False,
        regeneration_required=False,
        has_user_edits=False,
    )

    assert status.active_job is None
    assert status.last_job is None


def test_status_response_with_jobs():
    from app.schemas.brd import BRDStatusResponse

    job_id = uuid4()
    status = BRDStatusResponse(
        has_brd=False,
        has_sources=True,
        has_new_sources=True,
        regeneration_required=False,
        has_user_edits=False,
        active_job={
            "job_id": job_id,
            "status": "running",
            "phase": "processing_sources",
            "error": None,
        },
        last_job={
            "job_id": job_id,
            "status": "running",
            "phase": "processing_sources",
            "error": None,
        },
    )

    assert status.active_job is not None
    assert status.active_job.job_id == job_id
    assert status.active_job.phase == "processing_sources"
    assert status.last_job is not None
    assert status.last_job.status == "running"


def test_concurrent_guard_returns_active_job():
    service = make_service()
    active = make_job(status="running", phase="processing_sources")

    service.workspace_service.get_workspace_for_user = MagicMock(
        return_value=MagicMock(source_revision=0),
    )
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(return_value=active)
    )

    result = service.create_job_for_user(active.workspace_id, active.user_id)

    assert result is active
    service.db.add.assert_not_called()


def test_prune_keeps_latest_three():
    service = make_service()
    workspace_id = uuid4()
    jobs = [make_job(workspace_id=workspace_id) for _ in range(5)]

    deleted = []
    service.generation_job_repository.list_by_workspace_id_desc = (
        MagicMock(return_value=jobs)
    )
    service.generation_job_repository.delete = MagicMock(
        side_effect=lambda job: deleted.append(job),
    )

    service._prune_jobs(workspace_id, MAX_JOBS_PER_WORKSPACE)

    assert MAX_JOBS_PER_WORKSPACE == 3
    assert deleted == jobs[3:]


def test_execute_job_full_pipeline_succeeds():
    service = make_service()
    job = make_job()
    service.db.get = MagicMock(return_value=job)
    service.standard_document_repository.has_unextracted_by_workspace_id = (
        MagicMock(return_value=True)
    )

    phases = []
    real_set_phase = service._set_phase

    def record_phase(job_arg, status, phase):
        phases.append((status, phase))
        job_arg.status = status
        job_arg.phase = phase

    service._set_phase = MagicMock(side_effect=record_phase)

    import app.services.generation_job_service as job_module

    job_module.DocumentExtractionService = MagicMock()
    job_module.ProjectKnowledgeService = MagicMock()
    job_module.BRDService = MagicMock()

    try:
        extraction_service = (
            job_module.DocumentExtractionService.return_value
        )
        extraction_service.extract_workspace_documents = MagicMock(
            return_value=MagicMock(),
        )
        knowledge_service = job_module.ProjectKnowledgeService.return_value
        knowledge_service.consolidate_project_knowledge = MagicMock(
            return_value=MagicMock(),
        )
        brd_service = job_module.BRDService.return_value
        brd_service.generate_brd_for_user = MagicMock(
            return_value=MagicMock(),
        )

        service.execute_job(job.id)
    finally:
        import importlib

        importlib.reload(job_module)

    assert job.status == "succeeded"
    assert phases == [
        ("running", "processing_sources"),
        ("running", "preparing_knowledge"),
        ("running", "generating_brd"),
        ("succeeded", None),
    ]


def test_execute_job_skips_extraction_without_new_sources():
    service = make_service()
    job = make_job()
    service.db.get = MagicMock(return_value=job)
    service.standard_document_repository.has_unextracted_by_workspace_id = (
        MagicMock(return_value=False)
    )

    phases = []

    def record_phase(job_arg, status, phase):
        phases.append((status, phase))
        job_arg.status = status
        job_arg.phase = phase

    service._set_phase = MagicMock(side_effect=record_phase)

    import app.services.generation_job_service as job_module

    job_module.DocumentExtractionService = MagicMock()
    job_module.ProjectKnowledgeService = MagicMock()
    job_module.BRDService = MagicMock()

    try:
        extraction_service = (
            job_module.DocumentExtractionService.return_value
        )
        extraction_service.extract_workspace_documents = MagicMock(
            return_value=MagicMock(),
        )
        knowledge_service = job_module.ProjectKnowledgeService.return_value
        knowledge_service.consolidate_project_knowledge = MagicMock(
            return_value=MagicMock(),
        )
        brd_service = job_module.BRDService.return_value
        brd_service.generate_brd_for_user = MagicMock(
            return_value=MagicMock(),
        )

        service.execute_job(job.id)
    finally:
        import importlib

        importlib.reload(job_module)

    extraction_service.extract_workspace_documents.assert_not_called()
    assert job.status == "succeeded"
    assert phases == [
        ("running", "preparing_knowledge"),
        ("running", "generating_brd"),
        ("succeeded", None),
    ]


def test_execute_job_marks_failed_on_pipeline_error():
    service = make_service()
    job = make_job()
    service.db.get = MagicMock(return_value=job)
    service.standard_document_repository.has_unextracted_by_workspace_id = (
        MagicMock(return_value=False)
    )

    import app.services.generation_job_service as job_module

    job_module.DocumentExtractionService = MagicMock()
    job_module.ProjectKnowledgeService = MagicMock()
    job_module.BRDService = MagicMock()

    try:
        knowledge_service = job_module.ProjectKnowledgeService.return_value
        knowledge_service.consolidate_project_knowledge = MagicMock(
            return_value=None,
        )

        service.execute_job(job.id)
    finally:
        import importlib

        importlib.reload(job_module)

    assert job.status == "failed"
    assert job.error is not None


# --- H-3: stale-job reaper + create-vs-create race ---


def _minutes_ago(minutes):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_reap_stale_running_job_marks_failed():
    service = make_service()
    ghost = make_job(
        status="running",
        phase="generating_brd",
        updated_at=_minutes_ago(30),
    )
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(side_effect=[ghost, None])
    )

    reaped = service.reap_stale_jobs(ghost.workspace_id)

    assert reaped == 1
    assert ghost.status == "failed"
    assert ghost.error == STALE_JOB_MESSAGE
    service.db.commit.assert_called()


def test_reap_stale_queued_job_marks_failed():
    service = make_service()
    ghost = make_job(status="queued", updated_at=_minutes_ago(60))
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(side_effect=[ghost, None])
    )

    assert service.reap_stale_jobs(ghost.workspace_id) == 1
    assert ghost.status == "failed"
    assert ghost.error == STALE_JOB_MESSAGE


def test_reap_fresh_job_untouched():
    service = make_service()
    live = make_job(
        status="running",
        phase="processing_sources",
        updated_at=_minutes_ago(2),
    )
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(return_value=live)
    )

    assert service.reap_stale_jobs(live.workspace_id) == 0
    assert live.status == "running"
    service.db.commit.assert_not_called()


def test_reap_skips_job_without_timestamps():
    service = make_service()
    job = make_job(status="running")
    job.created_at = None
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(return_value=job)
    )

    assert service.reap_stale_jobs(job.workspace_id) == 0
    assert job.status == "running"


def test_reap_drains_multiple_stale_jobs():
    service = make_service()
    workspace_id = uuid4()
    ghost_old = make_job(
        workspace_id=workspace_id,
        status="running",
        updated_at=_minutes_ago(40),
    )
    ghost_new = make_job(
        workspace_id=workspace_id,
        status="queued",
        updated_at=_minutes_ago(25),
    )
    live = make_job(
        workspace_id=workspace_id,
        status="running",
        updated_at=_minutes_ago(1),
    )
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(side_effect=[ghost_old, ghost_new, live])
    )

    assert service.reap_stale_jobs(workspace_id) == 2
    assert ghost_old.status == "failed"
    assert ghost_new.status == "failed"
    assert live.status == "running"


def test_is_stale_treats_naive_datetimes_as_utc():
    service = make_service()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)

    stale_naive = make_job(
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(minutes=30),
    )
    fresh_naive = make_job(
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(minutes=1),
    )

    assert service._is_stale(stale_naive, cutoff) is True
    assert service._is_stale(fresh_naive, cutoff) is False


def test_create_reaps_before_checking_active():
    service = make_service()
    workspace_id = uuid4()
    user_id = uuid4()
    created = make_job(workspace_id=workspace_id, user_id=user_id)

    service.workspace_service.get_workspace_for_user = MagicMock(
        return_value=MagicMock(source_revision=0),
    )
    service.reap_stale_jobs = MagicMock(return_value=0)
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(return_value=None)
    )
    service.generation_job_repository.create = MagicMock(
        return_value=created,
    )
    service._prune_jobs = MagicMock()

    result = service.create_job_for_user(workspace_id, user_id)

    assert result is created
    service.reap_stale_jobs.assert_called_once_with(workspace_id)


def test_create_adopts_existing_job_on_integrity_error():
    service = make_service()
    workspace_id = uuid4()
    user_id = uuid4()
    winner = make_job(
        workspace_id=workspace_id,
        user_id=user_id,
        status="running",
        updated_at=_minutes_ago(1),
    )

    service.workspace_service.get_workspace_for_user = MagicMock(
        return_value=MagicMock(source_revision=0),
    )
    service.reap_stale_jobs = MagicMock(return_value=0)
    service.generation_job_repository.get_active_by_workspace_id = (
        MagicMock(side_effect=[None, winner])
    )
    service.generation_job_repository.create = MagicMock(
        side_effect=IntegrityError(
            "INSERT INTO generation_jobs",
            {},
            Exception("duplicate key"),
        ),
    )
    service._prune_jobs = MagicMock()

    result = service.create_job_for_user(workspace_id, user_id)

    assert result is winner
    service.db.rollback.assert_called()
    service.db.commit.assert_not_called()


def test_ghost_drill_real_sqlite_roundtrip():
    """End-to-end ghost drill against real SQL (not mocks): a stale
    running row orphaned 30 min ago is terminalized on reap, while a
    fresh job in another workspace is untouched."""

    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _register_uuid(dbapi_connection, _connection_record):
        # The id PK defaults to gen_random_uuid() (Postgres-only).
        dbapi_connection.create_function(
            "gen_random_uuid", 0, lambda: uuid4().hex
        )

    GenerationJob.__table__.create(engine)
    db = Session(engine)

    ghost_workspace = uuid4()
    ghost = GenerationJob(
        workspace_id=ghost_workspace,
        user_id=uuid4(),
        status="running",
        source_revision=3,
    )
    ghost.phase = "generating_brd"
    ghost.created_at = _minutes_ago(35)
    ghost.updated_at = _minutes_ago(30)

    live_workspace = uuid4()
    live = GenerationJob(
        workspace_id=live_workspace,
        user_id=uuid4(),
        status="running",
        source_revision=1,
    )
    live.phase = "processing_sources"

    db.add_all([ghost, live])
    db.commit()

    try:
        service = GenerationJobService(db)

        assert service.reap_stale_jobs(ghost_workspace) == 1
        assert service.reap_stale_jobs(live_workspace) == 0

        db.expire_all()
        ghost_row = (
            db.query(GenerationJob)
            .filter(GenerationJob.workspace_id == ghost_workspace)
            .one()
        )
        live_row = (
            db.query(GenerationJob)
            .filter(GenerationJob.workspace_id == live_workspace)
            .one()
        )

        assert ghost_row.status == "failed"
        assert ghost_row.error == STALE_JOB_MESSAGE
        assert ghost_row.source_revision == 3
        assert live_row.status == "running"
        assert live_row.phase == "processing_sources"
    finally:
        db.close()
