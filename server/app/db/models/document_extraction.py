from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

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
    )

    document_knowledge: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    raw_sarvam_response: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
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
        back_populates="document_extractions",
    )

    source_documents: Mapped[
        list["DocumentExtractionDocument"]
    ] = relationship(
        back_populates="document_extraction",
        cascade="all, delete-orphan",
    )
