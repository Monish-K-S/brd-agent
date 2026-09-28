import tempfile
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.integrations.drive.service import (
    DRIVE_DOWNLOAD_MIMETYPES,
    DriveService,
)
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.standard_document_service import StandardDocumentService
from sqlalchemy.orm import Session


class DriveImportService:
    """
    Imports a user-selected Google Drive file into a workspace as a
    StandardDocument record.

    Drive-specific API handling stays in DriveService.
    Bytes enter the existing pipeline via DocumentIngestionService
    (parser factory -> parse -> normalize).
    Database persistence stays in StandardDocumentService.
    """

    def __init__(self, db: Session):
        self.db = db

        self.drive_service = DriveService(db)
        self.document_repository = StandardDocumentRepository(db)
        self.document_service = StandardDocumentService(db)
        self.ingestion_service = DocumentIngestionService()

    def import_file(
        self,
        workspace_id: UUID,
        user_id: UUID,
        drive_file_id: str,
    ) -> tuple[object, bool]:
        existing_document = (
            self.document_repository.get_by_drive_file_id(
                workspace_id=workspace_id,
                drive_file_id=drive_file_id,
            )
        )

        if existing_document is not None:
            return existing_document, True

        metadata = self.drive_service.get_file_metadata(
            user_id=user_id,
            file_id=drive_file_id,
        )

        mime_type = metadata.get("mimeType", "")
        file_name = metadata.get("name") or drive_file_id

        if mime_type.startswith("application/vnd.google-apps."):
            raise ValueError(
                f"Unsupported file type: {file_name}. "
                "Google-native files (Docs, Sheets, Slides) cannot be "
                "imported directly. Download it as PDF, DOCX, or TXT "
                "and upload it instead."
            )

        suffix = DRIVE_DOWNLOAD_MIMETYPES.get(mime_type)

        if suffix is None:
            raise ValueError(
                f"Unsupported file type: {file_name} ({mime_type}). "
                "Only PDF, DOCX, and TXT files can be imported."
            )

        declared_size = metadata.get("size")

        if declared_size is not None and int(declared_size) > (
            settings.max_upload_bytes
        ):
            raise ValueError(
                f"File too large: {file_name}. "
                "Maximum file size is 10 MB."
            )

        file_bytes = self.drive_service.download_file(
            user_id=user_id,
            file_id=drive_file_id,
        )

        if len(file_bytes) > settings.max_upload_bytes:
            raise ValueError(
                f"File too large: {file_name}. "
                "Maximum file size is 10 MB."
            )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:
                temp_file.write(file_bytes)
                temp_path = Path(temp_file.name)

            documents = self.ingestion_service.ingest(temp_path)

            for document in documents:
                document.title = file_name
                document.metadata["file_name"] = file_name
                document.metadata["drive_file_id"] = drive_file_id
                document.metadata["mime_type"] = mime_type
                document.metadata["extension"] = suffix
                document.metadata["size_bytes"] = len(file_bytes)

                web_view_link = metadata.get("webViewLink")

                if web_view_link:
                    document.metadata["drive_web_view_link"] = web_view_link

        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

        if not documents:
            raise ValueError(
                f"No readable content found in file: {file_name}."
            )

        created_documents = (
            self.document_service.create_documents_from_ingestion(
                workspace_id=workspace_id,
                user_id=user_id,
                documents=documents,
            )
        )

        if created_documents is None:
            raise ValueError("Workspace not found.")

        return created_documents[0], False
