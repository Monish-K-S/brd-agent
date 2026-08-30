from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.document_extraction import DocumentExtraction
from app.db.models.document_extraction_document import (
    DocumentExtractionDocument,
)
from app.db.models.standard_document import StandardDocument


class DocumentExtractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        extraction_id: UUID,
    ) -> DocumentExtraction | None:
        return self.db.get(
            DocumentExtraction,
            extraction_id,
        )

    def get_all_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> list[DocumentExtraction]:
        return (
            self.db.query(DocumentExtraction)
            .filter(
                DocumentExtraction.workspace_id == workspace_id,
            )
            .order_by(
                DocumentExtraction.created_at.asc(),
            )
            .all()
        )

    def create(
        self,
        extraction: DocumentExtraction,
    ) -> DocumentExtraction:
        self.db.add(extraction)
        self.db.flush()
        self.db.refresh(extraction)

        return extraction

    def link_source_documents(
        self,
        extraction_id: UUID,
        document_ids: list[UUID],
    ) -> None:
        mappings = [
            DocumentExtractionDocument(
                document_extraction_id=extraction_id,
                standard_document_id=document_id,
            )
            for document_id in document_ids
        ]

        self.db.add_all(mappings)
        self.db.flush()

    def get_source_documents(
        self,
        extraction_id: UUID,
    ) -> list[StandardDocument]:
        return (
            self.db.query(StandardDocument)
            .join(
                DocumentExtractionDocument,
                DocumentExtractionDocument.standard_document_id == StandardDocument.id,
            )
            .filter(
                DocumentExtractionDocument.document_extraction_id == extraction_id,
            )
            .order_by(StandardDocument.created_at.asc())
            .all()
        )


    def get_extracted_document_ids(
        self,
        workspace_id: UUID,
    ) -> list[UUID]:
        rows = (
            self.db.query(
                DocumentExtractionDocument.standard_document_id,
            )
            .join(
                DocumentExtraction,
                DocumentExtractionDocument.document_extraction_id
                == DocumentExtraction.id,
            )
            .filter(
                DocumentExtraction.workspace_id == workspace_id,
            )
            .all()
        )

        return [
            row.standard_document_id
            for row in rows
        ]
