import logging
import re
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
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

logger = logging.getLogger("brd-agent.generation")


MAX_JOBS_PER_WORKSPACE = 3

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

PHASE_PROCESSING_SOURCES = "processing_sources"
PHASE_PREPARING_KNOWLEDGE = "preparing_knowledge"
PHASE_GENERATING_BRD = "generating_brd"

STALE_JOB_MESSAGE = "Server restarted mid-run — please regenerate."

GENERIC_FAILURE_MESSAGE = (
    "Something went wrong while generating the BRD. "
    "Please try again."
)
BUSY_MESSAGE = (
    "The AI service is busy right now — try again "
    "in a few minutes."
)
SAFETY_MESSAGE = (
    "The request was blocked by the AI safety filters — "
    "try rephrasing your question or removing "
    "restricted content."
)
UNREACHABLE_MESSAGE = (
    "Couldn't reach the AI service — check your "
    "connection and try again."
)
CONFIG_MESSAGE = (
    "The AI service isn't configured correctly on this "
    "server — please contact the operator."
)


def public_error_message(exc: Exception) -> str:
    """User-safe failure text for ``job.error``.

    Raw ``str(exc)`` from google-genai / sarvamai / SQLAlchemy is persisted on
    the job and rendered verbatim by the client, so it must never leave the
    server — the detail belongs in the log instead (see ``execute_job``).
    Known conditions map to friendly copy; anything unrecognized falls back
    to the generic message. Bare status codes are matched with word
    boundaries so an id or path containing "429" cannot misfire.
    """
    text = f"{type(exc).__name__} {exc}".lower()

    if re.search(
        r"\b429\b|rate[ _-]?limit|quota"
        r"|resource[ _-]?exhausted|too many requests",
        text,
    ):
        return BUSY_MESSAGE

    if re.search(
        r"safety|prohibited|content[ _-]?filter"
        r"|blocked by|recitation",
        text,
    ):
        return SAFETY_MESSAGE

    if isinstance(exc, (TimeoutError, ConnectionError)) or re.search(
        r"timeout|timed out|deadline|unavailable"
        r"|connection (?:refused|reset|error)|max retries",
        text,
    ):
        return UNREACHABLE_MESSAGE

    if re.search(
        r"api[ _-]?key|not set|unauthorized"
        r"|permission denied|permission_denied"
        r"|forbidden|unauthenticated",
        text,
    ):
        return CONFIG_MESSAGE

    return GENERIC_FAILURE_MESSAGE


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

        # Ghost jobs (queued/running rows orphaned by a server restart)
        # would otherwise block every future generate: reap them first so
        # the active-check below sees the true state.
        self.reap_stale_jobs(workspace_id)

        for _ in range(2):
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
            except IntegrityError:
                # Lost the create-vs-create race against a concurrent
                # generate: the partial unique index kept exactly one
                # active job — loop back and adopt it instead of 409ing.
                self.db.rollback()
                continue
            except Exception:
                self.db.rollback()
                raise

        return self.generation_job_repository.get_active_by_workspace_id(
            workspace_id,
        )

    def reap_stale_jobs(
        self,
        workspace_id: UUID,
    ) -> int:
        """Terminalize orphaned jobs: queued/running rows untouched longer
        than the timeout (the in-process worker died — typically a server
        restart mid-run). Returns the number of jobs reaped."""

        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.generation_job_timeout_minutes,
        )

        reaped = 0

        while True:
            active_job = (
                self.generation_job_repository.get_active_by_workspace_id(
                    workspace_id,
                )
            )

            if active_job is None or not self._is_stale(
                active_job,
                cutoff,
            ):
                return reaped

            self._fail_job(
                active_job,
                STALE_JOB_MESSAGE,
            )

            reaped += 1

    @staticmethod
    def _is_stale(
        job: GenerationJob,
        cutoff: datetime,
    ) -> bool:
        seen_at = job.updated_at or job.created_at

        if seen_at is None:
            # Never persisted (no heartbeat yet) — treat as fresh.
            return False

        if seen_at.tzinfo is None:
            seen_at = seen_at.replace(tzinfo=timezone.utc)

        return seen_at < cutoff

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

        job_started = time.perf_counter()

        try:
            if has_new_sources:
                self._set_phase(
                    job,
                    STATUS_RUNNING,
                    PHASE_PROCESSING_SOURCES,
                )

                phase_started = time.perf_counter()

                extraction = (
                    extraction_service.extract_workspace_documents(
                        workspace_id=workspace_id,
                        user_id=user_id,
                    )
                )

                self._log_phase(
                    job_id,
                    PHASE_PROCESSING_SOURCES,
                    phase_started,
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

            phase_started = time.perf_counter()

            project_knowledge = (
                project_knowledge_service.consolidate_project_knowledge(
                    workspace_id=workspace_id,
                    user_id=user_id,
                )
            )

            self._log_phase(
                job_id,
                PHASE_PREPARING_KNOWLEDGE,
                phase_started,
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

            phase_started = time.perf_counter()

            brd = brd_service.generate_brd_for_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )

            self._log_phase(
                job_id,
                PHASE_GENERATING_BRD,
                phase_started,
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

            logger.info(
                "Generation job %s succeeded in %.2fs",
                job_id,
                time.perf_counter() - job_started,
            )
        except Exception as exc:
            logger.exception(
                "Generation job %s failed (workspace %s) after %.2fs",
                job_id,
                workspace_id,
                time.perf_counter() - job_started,
            )

            self._fail_job(
                job,
                public_error_message(exc),
            )

    def _get_job(
        self,
        job_id: UUID,
    ) -> GenerationJob | None:
        return self.db.get(
            GenerationJob,
            job_id,
        )

    @staticmethod
    def _log_phase(
        job_id: UUID,
        phase: str,
        started: float,
    ) -> None:
        """Wall-clock cost of one pipeline phase (observability only).

        Extraction and BRD generation are remote calls, so without this
        there is no way to tell which stage is slow (or whether the
        aggregate-PDF build is a factor) from the logs.
        """
        logger.info(
            "Generation job %s phase=%s took %.2fs",
            job_id,
            phase,
            time.perf_counter() - started,
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
