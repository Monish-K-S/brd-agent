"""Generation job lifecycle (Phase 2b).

Covers the async BRD pipeline without a database: schema backward
compatibility (old 5-field status payloads still parse), the
server-side concurrent guard, prune-to-latest-3, and the unified
worker pipeline with phase transitions — all with mocked sessions.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import app.db.models.google_connection  # noqa: F401 — registers mapper
from app.db.models.generation_job import GenerationJob
from app.services.generation_job_service import (
    GenerationJobService,
    MAX_JOBS_PER_WORKSPACE,
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
