import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_db_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.standard_document import StandardDocumentResponse
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


@router.post(
    "/upload",
    response_model=list[StandardDocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[StandardDocumentResponse]:
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
                "Unsupported file type. "
                "Supported types: .txt, .pdf, .docx"
            ),
        )

    ingestion_service = DocumentIngestionService()
    document_service = StandardDocumentService(db)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            shutil.copyfileobj(
                file.file,
                temp_file,
            )

            temp_path = Path(temp_file.name)

        documents = ingestion_service.ingest(
            temp_path,
        )

        created_documents = (
            document_service.create_documents_from_ingestion(
                workspace_id=workspace_id,
                user_id=current_user.id,
                documents=documents,
            )
        )

        if created_documents is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found",
            )

        return [
            StandardDocumentResponse(
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
            for document in created_documents
        ]

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

        file.file.close()
