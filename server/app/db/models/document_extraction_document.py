from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentExtractionDocument(Base):
    __tablename__ = "document_extraction_documents"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    __table_args__ = (
        UniqueConstraint(
            "document_extraction_id",
            "standard_document_id",
            name="uq_extraction_document",
        ),
    )

    document_extraction_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "document_extractions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    standard_document_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "standard_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        # The composite unique above leads with document_extraction_id,
        # so it cannot serve lookups by standard_document_id alone —
        # which is exactly what the ORM cascade issues when a document
        # is deleted.
        index=True,
    )

    document_extraction: Mapped["DocumentExtraction"] = relationship(
        back_populates="source_documents",
    )

    standard_document: Mapped["StandardDocument"] = relationship(
        back_populates="extraction_links",
    )
