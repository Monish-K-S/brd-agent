from uuid import UUID

from app.core.config import settings
from app.integrations.gmail.mapper import GmailEmailMapper
from app.integrations.gmail.service import GmailService
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.standard_document_service import StandardDocumentService
from sqlalchemy.orm import Session


class GmailImportService:
    """
    Imports selected Gmail messages into a workspace as
    StandardDocument records.

    Gmail-specific API handling stays in GmailService.
    Database persistence stays in StandardDocumentService.
    """

    def __init__(self, db: Session):
        self.db = db

        self.gmail_service = GmailService(db)
        self.document_repository = StandardDocumentRepository(db)
        self.document_service = StandardDocumentService(db)
        self.mapper = GmailEmailMapper()

    def import_messages(
        self,
        workspace_id: UUID,
        user_id: UUID,
        message_ids: list[str],
    ) -> tuple[list, list[str]]:
        imported_documents = []
        skipped_message_ids = []

        unique_message_ids = list(
            dict.fromkeys(message_ids),
        )

        for message_id in unique_message_ids:
            existing_document = self.document_repository.get_by_gmail_message_id(
                workspace_id=workspace_id,
                gmail_message_id=message_id,
            )

            if existing_document is not None:
                skipped_message_ids.append(message_id)
                continue

            message = self.gmail_service.get_message(
                user_id=user_id,
                message_id=message_id,
            )

            document = self.mapper.to_standard_document(
                message,
            )

            # Gmail bodies arrive with no size ceiling of their own, so
            # the upload path's per-document cap is enforced here too.
            # A single oversized message aborts the import (413) rather
            # than storing unbounded text.
            if len(document.content) > settings.max_extracted_chars:
                raise ValueError(
                    f"Message too large: {message_id}. "
                    "Maximum extracted size is "
                    f"{settings.max_extracted_chars} characters."
                )

            imported_documents.append(document)

        if not imported_documents:
            return [], skipped_message_ids

        created_documents = self.document_service.create_documents_from_ingestion(
            workspace_id=workspace_id,
            user_id=user_id,
            documents=imported_documents,
        )

        if created_documents is None:
            raise ValueError("Workspace not found.")

        return created_documents, skipped_message_ids
