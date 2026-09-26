from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GenerationJob(Base):
    """Async BRD pipeline run (extract → consolidate → generate).

    Created by POST /brd/generate, executed by an in-process background
    task, polled via GET /brd/status (active_job). History is pruned to
    the latest 3 jobs per workspace on creation.
    """

    __tablename__ = "generation_jobs"

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
