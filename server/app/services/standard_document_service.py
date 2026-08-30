from uuid import UUID

from sqlalchemy.orm import Session

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
