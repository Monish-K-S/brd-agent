from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.document_extraction import DocumentExtraction
from app.repositories.document_extraction_repository import (
    DocumentExtractionRepository,
)
from app.services.workspace_service import WorkspaceService
from app.services.standard_document_service import (
    StandardDocumentService,
)


class DocumentExtractionService:
    def __init__(self, db: Session):
        self.db = db

        self.extraction_repository = (
            DocumentExtractionRepository(db)
        )

        self.workspace_service = WorkspaceService(db)

        self.document_service = StandardDocumentService(db)

    def get_extraction_for_user(
        self,
        extraction_id: UUID,
        user_id: UUID,
    ) -> DocumentExtraction | None:
        extraction = self.extraction_repository.get_by_id(
            extraction_id,
        )

        if extraction is None:
            return None

        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=extraction.workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return extraction



    def get_workspace_extractions_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[DocumentExtraction] | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return self.extraction_repository.get_all_by_workspace_id(
            workspace_id,
        )



    def get_extracted_document_ids_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[UUID] | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return self.extraction_repository.get_extracted_document_ids(
            workspace_id,
        )



    def create_extraction(
        self,
        workspace_id: UUID,
        user_id: UUID,
        document_knowledge: dict,
        source_document_ids: list[UUID],
        raw_sarvam_response: dict | None = None,
    ) -> DocumentExtraction | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        for document_id in source_document_ids:
            document = self.document_service.get_document_for_user(
                document_id=document_id,
                user_id=user_id,
            )

            if document is None:
                return None

            if document.workspace_id != workspace_id:
                return None

        try:
            extraction = DocumentExtraction(
                workspace_id=workspace_id,
                document_knowledge=document_knowledge,
                source_document_ids=[
                    str(document_id)
                    for document_id in source_document_ids
                ],
                raw_sarvam_response=raw_sarvam_response,
            )

            created_extraction = self.extraction_repository.create(
                extraction,
            )

            self.extraction_repository.link_source_documents(
                extraction_id=created_extraction.id,
                document_ids=source_document_ids,
            )

            self.db.commit()

            return created_extraction

        except Exception:
            self.db.rollback()
            raise
