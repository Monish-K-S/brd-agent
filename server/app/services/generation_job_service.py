from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.generation_job import GenerationJob
from app.db.session import SessionLocal
from app.repositories.generation_job_repository import (
    GenerationJobRepository,
)
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.brd_service import BRDService
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)
from app.services.workspace_service import WorkspaceService


MAX_JOBS_PER_WORKSPACE = 3

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

PHASE_PROCESSING_SOURCES = "processing_sources"
PHASE_PREPARING_KNOWLEDGE = "preparing_knowledge"
PHASE_GENERATING_BRD = "generating_brd"


class GenerationJobService:
    def __init__(self, db: Session):
        self.db = db

        self.generation_job_repository = GenerationJobRepository(db)

        self.standard_document_repository = StandardDocumentRepository(db)

        self.workspace_service = WorkspaceService(db)

    def create_job_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> GenerationJob | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        active_job = (
            self.generation_job_repository.get_active_by_workspace_id(
                workspace_id,
            )
        )

        if active_job is not None:
            return active_job

        job = GenerationJob(
            workspace_id=workspace_id,
            user_id=user_id,
            status=STATUS_QUEUED,
            source_revision=workspace.source_revision,
        )

        try:
            created_job = self.generation_job_repository.create(job)

            self._prune_jobs(
                workspace_id=workspace_id,
                keep=MAX_JOBS_PER_WORKSPACE,
            )

            self.db.commit()

            self.db.refresh(created_job)

            return created_job
        except Exception:
            self.db.rollback()
            raise

    def execute_job(
        self,
        job_id: UUID,
    ) -> None:
        job = self._get_job(job_id)

        if job is None or job.status in (
            STATUS_SUCCEEDED,
            STATUS_FAILED,
        ):
            return

        workspace_id = job.workspace_id
        user_id = job.user_id

        extraction_service = DocumentExtractionService(self.db)
        project_knowledge_service = ProjectKnowledgeService(self.db)
        brd_service = BRDService(self.db)

        has_new_sources = (
            self.standard_document_repository.has_unextracted_by_workspace_id(
                workspace_id,
            )
        )

        try:
            if has_new_sources:
                self._set_phase(
                    job,
                    STATUS_RUNNING,
                    PHASE_PROCESSING_SOURCES,
                )

                extraction = (
                    extraction_service.extract_workspace_documents(
                        workspace_id=workspace_id,
                        user_id=user_id,
                    )
                )

                if extraction is None:
                    self._fail_job(
                        job,
                        "Workspace not found or no new sources to extract",
                    )

                    return

            self._set_phase(
                job,
                STATUS_RUNNING,
                PHASE_PREPARING_KNOWLEDGE,
            )

            project_knowledge = (
                project_knowledge_service.consolidate_project_knowledge(
                    workspace_id=workspace_id,
                    user_id=user_id,
                )
            )

            if project_knowledge is None:
                self._fail_job(
                    job,
                    "Workspace not found or no extracted knowledge available",
                )

                return

            self._set_phase(
                job,
                STATUS_RUNNING,
                PHASE_GENERATING_BRD,
            )

            brd = brd_service.generate_brd_for_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )

            if brd is None:
                self._fail_job(
                    job,
                    "Workspace not found or project knowledge not available",
                )

                return

            self._set_phase(
                job,
                STATUS_SUCCEEDED,
                None,
            )
        except Exception as exc:
            self._fail_job(
                job,
                str(exc) or "Generation failed",
            )

    def _get_job(
        self,
        job_id: UUID,
    ) -> GenerationJob | None:
        return self.db.get(
            GenerationJob,
            job_id,
        )

    def _set_phase(
        self,
        job: GenerationJob,
        status: str,
        phase: str | None,
    ) -> None:
        try:
            job.status = status
            job.phase = phase

            self.generation_job_repository.update(job)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _fail_job(
        self,
        job: GenerationJob,
        error: str,
    ) -> None:
        try:
            job.status = STATUS_FAILED
            job.error = error

            self.generation_job_repository.update(job)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _prune_jobs(
        self,
        workspace_id: UUID,
        keep: int,
    ) -> None:
        jobs = (
            self.generation_job_repository.list_by_workspace_id_desc(
                workspace_id,
            )
        )

        for job in jobs[keep:]:
            self.generation_job_repository.delete(job)


def run_generation_job(job_id: UUID) -> None:
    """Background-task entry point. Own session: the request session that
    created the job is closed once the 202 response is sent."""

    db = SessionLocal()

    try:
        service = GenerationJobService(db)
        service.execute_job(job_id)
    finally:
        db.close()
