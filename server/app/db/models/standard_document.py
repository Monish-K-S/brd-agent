from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StandardDocument(Base):
    __tablename__ = "standard_documents"

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

    source_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    author: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    source_created_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    participants: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_extracted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
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
        back_populates="standard_documents",
    )

    extraction_links: Mapped[
        list["DocumentExtractionDocument"]
    ] = relationship(
        back_populates="standard_document",
        cascade="all, delete-orphan",
    )
