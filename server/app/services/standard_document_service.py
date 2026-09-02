from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.models.standard_document import (
    StandardDocument as AIStandardDocument,
)
from app.db.models.standard_document import StandardDocument
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.workspace_service import WorkspaceService


class StandardDocumentService:
    def __init__(self, db: Session):
        self.db = db

        self.document_repository = StandardDocumentRepository(
            db,
        )

        self.workspace_service = WorkspaceService(
            db,
        )

    def get_document_for_user(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> StandardDocument | None:
        document = self.document_repository.get_by_id(
            document_id,
        )

        if document is None:
            return None

        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=document.workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return document

    def get_workspace_documents_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[StandardDocument] | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return self.document_repository.get_all_by_workspace_id(
            workspace_id,
        )

    def create_document(
        self,
        workspace_id: UUID,
        user_id: UUID,
        source_type: str,
        content: str,
        title: str | None = None,
        author: str | None = None,
        source_created_at: datetime | None = None,
        participants: list | None = None,
        metadata_: dict | None = None,
    ) -> StandardDocument | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        document = StandardDocument(
            workspace_id=workspace_id,
            source_type=source_type,
            title=title,
            author=author,
            source_created_at=source_created_at,
            participants=participants or [],
            content=content,
            metadata_=metadata_ or {},
        )

        created_document = self.document_repository.create(
            document,
        )

        self.db.commit()

        return created_document

    def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> bool:
        document = self.get_document_for_user(
            document_id=document_id,
            user_id=user_id,
        )

        if document is None:
            return False

        self.document_repository.delete(document)

        self.db.commit()

        return True


def create_documents_from_ingestion(
    self,
    workspace_id: UUID,
    user_id: UUID,
    documents: list[AIStandardDocument],
) -> list[StandardDocument] | None:
    """
    Store parsed AI-layer StandardDocuments
    as database StandardDocuments.
    """

    workspace = self.workspace_service.get_workspace_for_user(
        workspace_id=workspace_id,
        user_id=user_id,
    )

    if workspace is None:
        return None

    db_documents = []

    for document in documents:
        db_document = StandardDocument(
            workspace_id=workspace_id,
            source_type=document.source_type,
            title=document.title,
            author=document.author,
            source_created_at=document.created_at,
            participants=document.participants,
            content=document.content,
            metadata_=document.metadata,
        )

        db_documents.append(db_document)

    created_documents = self.document_repository.create_many(
        db_documents,
    )

    self.db.commit()

    return created_documents
