import tempfile
import zipfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_db_user
from app.core.audit import audit
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.standard_document import (
    StandardDocumentResponse,
    StandardDocumentSummary,
)
from app.services.document_ingestion_service import (
    DocumentIngestionService,
)
from app.services.standard_document_service import (
    StandardDocumentService,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/documents",
    tags=["Documents"],
)


_CHUNK_SIZE = 64 * 1024


class _FileTooLargeError(ValueError):
    pass


def _copy_upload_with_limit(file: UploadFile, dest_path: str) -> int:
    total = 0

    with open(dest_path, "wb") as dest:
        while True:
            chunk = file.file.read(_CHUNK_SIZE)

            if not chunk:
                break

            total += len(chunk)

            if total > settings.max_upload_bytes:
                raise _FileTooLargeError(
                    f"File too large: {file.filename} "
                    f"(max {settings.max_upload_bytes // (1024 * 1024)}MB)"
                )

            dest.write(chunk)

    return total


def _validate_file_magic(path: Path, suffix: str) -> bool:
    try:
        if suffix == ".pdf":
            with open(path, "rb") as handle:
                return handle.read(5) == b"%PDF-"

        if suffix == ".docx":
            with open(path, "rb") as handle:
                if handle.read(4) != b"PK\x03\x04":
                    return False

            try:
                with zipfile.ZipFile(path) as archive:
                    return (
                        "[Content_Types].xml" in archive.namelist()
                    )
            except zipfile.BadZipFile:
                return False

        if suffix == ".txt":
            with open(path, "rb") as handle:
                sample = handle.read(8192)

            if b"\x00" in sample:
                return False

            sample.decode("utf-8")

            return True

    except (OSError, UnicodeDecodeError):
        return False

    return False


def upload_file_key(
    file_name: str | None,
    extension: str | None,
    size_bytes: int | None,
) -> tuple:
    """Dedup triple: exact file name (case-sensitive), lowercase
    dot-extension, and exact byte size."""

    return (file_name, extension, size_bytes)


def stored_document_key(metadata: dict | None) -> tuple:
    metadata = metadata or {}

    return upload_file_key(
        metadata.get("file_name"),
        metadata.get("extension"),
        metadata.get("size_bytes"),
    )


def find_duplicate_upload(
    incoming_keys: list[tuple],
    existing_keys: set[tuple],
) -> tuple | None:
    """First incoming triple already stored or repeated in-batch."""

    seen = set()

    for key in incoming_keys:
        if key in existing_keys or key in seen:
            return key

        seen.add(key)

    return None


@router.post(
    "/upload",
    response_model=list[StandardDocumentSummary],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_upload)
def upload_documents(
    request: Request,
    workspace_id: UUID,
    files: Annotated[
        list[UploadFile],
        File(...),
    ],
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[StandardDocumentSummary]:

    ingestion_service = DocumentIngestionService()
    document_service = StandardDocumentService(db)

    all_documents = []

    if len(files) > settings.max_upload_files:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Too many files: {len(files)}. "
                f"Maximum {settings.max_upload_files} files per request"
            ),
        )

    existing_documents = (
        document_service.get_workspace_document_summaries_for_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    )

    if existing_documents is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    existing_keys = {
        stored_document_key(document.metadata_)
        for document in existing_documents
    }
    seen_keys = set()

    try:
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="File name is required",
                )

            suffix = Path(file.filename).suffix.lower()

            if suffix not in {".txt", ".pdf", ".docx"}:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported file type: {file.filename}. "
                        "Supported types: .txt, .pdf, .docx"
                    ),
                )

            temp_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix,
                ) as temp_file:
                    temp_path = Path(temp_file.name)

                try:
                    size_bytes = _copy_upload_with_limit(
                        file, str(temp_path)
                    )
                except _FileTooLargeError as exc:
                    raise HTTPException(
                        status_code=413,
                        detail=str(exc),
                    )

                if not _validate_file_magic(temp_path, suffix):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Unsupported file type: {file.filename}. "
                            "File content does not match its extension"
                        ),
                    )

                incoming_key = upload_file_key(
                    file.filename,
                    suffix,
                    size_bytes,
                )

                if (
                    incoming_key in existing_keys
                    or incoming_key in seen_keys
                ):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Duplicate file: {file.filename}. "
                            "A file with the same name, type, and size "
                            "already exists in this workspace"
                        ),
                    )

                seen_keys.add(incoming_key)

                try:
                    documents = ingestion_service.ingest(
                        temp_path,
                    )
                except _FileTooLargeError as exc:
                    raise HTTPException(
                        status_code=413,
                        detail=str(exc),
                    )
                except ValueError as exc:
                    message = str(exc)

                    if "too large" in message.lower():
                        raise HTTPException(
                            status_code=413,
                            detail=message,
                        )

                    raise HTTPException(
                        status_code=400,
                        detail=message,
                    )

                for document in documents:
                    document.title = file.filename
                    document.metadata["file_name"] = file.filename

                all_documents.extend(documents)

            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()

                file.file.close()

        if not all_documents:
            raise HTTPException(
                status_code=400,
                detail="No documents were created from uploaded files",
            )

        created_documents = (
            document_service.create_documents_from_ingestion(
                workspace_id=workspace_id,
                user_id=current_user.id,
                documents=all_documents,
            )
        )

        if created_documents is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found",
            )

        return [
            StandardDocumentSummary(
                id=document.id,
                workspace_id=document.workspace_id,
                source_type=document.source_type,
                title=document.title,
                author=document.author,
                source_created_at=document.source_created_at,
                participants=document.participants,
                metadata=document.metadata_,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document in created_documents
        ]

    except Exception:
        raise



@router.get(
    "",
    response_model=list[StandardDocumentSummary],
)
def get_workspace_documents(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[StandardDocumentSummary]:
    document_service = StandardDocumentService(db)

    documents = document_service.get_workspace_document_summaries_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if documents is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return [
        StandardDocumentSummary(
            id=document.id,
            workspace_id=document.workspace_id,
            source_type=document.source_type,
            title=document.title,
            author=document.author,
            source_created_at=document.source_created_at,
            participants=document.participants,
            metadata=document.metadata_,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        for document in documents
    ]



@router.get(
    "/{document_id}",
    response_model=StandardDocumentResponse,
)
def get_document(
    workspace_id: UUID,
    document_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> StandardDocumentResponse:
    document_service = StandardDocumentService(db)

    document = document_service.get_document_for_user(
        document_id=document_id,
        user_id=current_user.id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Important: ensure document belongs to the workspace in the URL
    if document.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return StandardDocumentResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        source_type=document.source_type,
        title=document.title,
        author=document.author,
        source_created_at=document.source_created_at,
        participants=document.participants,
        content=document.content,
        metadata=document.metadata_,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )



@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    workspace_id: UUID,
    document_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> None:
    document_service = StandardDocumentService(db)

    document = document_service.get_document_for_user(
        document_id=document_id,
        user_id=current_user.id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Prevent accessing a document through another workspace URL
    if document.workspace_id != workspace_id:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    deleted = document_service.delete_document(
        document_id=document_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    audit(
        event="document.delete",
        outcome="success",
        user_id=current_user.id,
        workspace_id=workspace_id,
    )
