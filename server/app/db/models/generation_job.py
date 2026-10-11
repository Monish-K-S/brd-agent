from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GenerationJob(Base):
    """Async BRD pipeline run (extract → consolidate → generate).

    Created by POST /brd/generate, executed by an in-process background
    task, polled via GET /brd/status (active_job). History is pruned to
    the latest 3 jobs per workspace on creation.
    """

    __tablename__ = "generation_jobs"

    __table_args__ = (
        # One queued/running job per workspace: closes the
        # create-vs-create race at the database level (the service
        # adopts the surviving job on IntegrityError). Partial index
        # lives in migration b8c9d0e1f2a3; mirrored here for metadata
        # truth (postgresql_where only compiles on Postgres).
        Index(
            "uq_generation_jobs_one_active_per_workspace",
            "workspace_id",
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "workspaces.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # queued | running | succeeded | failed
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="queued",
    )

    # processing_sources | preparing_knowledge | generating_brd | None
    phase: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="generation_jobs",
    )
