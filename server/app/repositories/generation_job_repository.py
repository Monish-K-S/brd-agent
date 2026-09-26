from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.generation_job import GenerationJob


TERMINAL_STATUSES = (
    "succeeded",
    "failed",
)


class GenerationJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> GenerationJob | None:
        return (
            self.db.query(GenerationJob)
            .filter(
                GenerationJob.workspace_id == workspace_id,
                ~GenerationJob.status.in_(TERMINAL_STATUSES),
            )
            .order_by(GenerationJob.created_at.desc())
            .first()
        )

    def get_latest_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> GenerationJob | None:
        return (
            self.db.query(GenerationJob)
            .filter(
                GenerationJob.workspace_id == workspace_id,
            )
            .order_by(GenerationJob.created_at.desc())
            .first()
        )

    def list_by_workspace_id_desc(
        self,
        workspace_id: UUID,
    ) -> list[GenerationJob]:
        return (
            self.db.query(GenerationJob)
            .filter(
                GenerationJob.workspace_id == workspace_id,
            )
            .order_by(GenerationJob.created_at.desc())
            .all()
        )

    def create(
        self,
        job: GenerationJob,
    ) -> GenerationJob:
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)

        return job

    def update(
        self,
        job: GenerationJob,
    ) -> GenerationJob:
        self.db.flush()
        self.db.refresh(job)

        return job

    def delete(
        self,
        job: GenerationJob,
    ) -> None:
        self.db.delete(job)
        self.db.flush()
