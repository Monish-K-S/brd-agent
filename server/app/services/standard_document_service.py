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

    def get_workspace_document_summaries_for_user(
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

        return self.document_repository.get_summaries_by_workspace_id(
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

        try:
            created_document = self.document_repository.create(
                document,
            )

            workspace.source_revision += 1

            self.db.commit()

            return created_document

        except Exception:
            self.db.rollback()
            raise

    def create_documents_from_ingestion(
        self,
        workspace_id: UUID,
        user_id: UUID,
        documents: list[AIStandardDocument],
    ) -> list[StandardDocument] | None:
        """
        Convert AI pipeline StandardDocument objects into database
        StandardDocument models and store them atomically.
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
                source_created_at=document.source_created_at,
                participants=document.participants,
                content=document.content,
                metadata_=document.metadata,
            )

            db_documents.append(db_document)

        try:
            created_documents = self.document_repository.create_many(
                db_documents,
            )

            if created_documents:
                workspace.source_revision += len(
                    created_documents,
                )

            self.db.commit()

            return created_documents

        except Exception:
            self.db.rollback()
            raise

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

        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=document.workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return False

        try:
            self.document_repository.delete(
                document,
            )

            workspace.source_revision += 1

            self.db.commit()

            return True

        except Exception:
            self.db.rollback()
            raise
