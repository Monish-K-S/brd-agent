import shutil
import tempfile
from pathlib import Path
from typing import Annotated
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
def upload_documents(
    workspace_id: UUID,
    files: Annotated[
        list[UploadFile],
        File(...),
    ],
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[StandardDocumentResponse]:

    ingestion_service = DocumentIngestionService()
    document_service = StandardDocumentService(db)

    all_documents = []

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
                    shutil.copyfileobj(
                        file.file,
                        temp_file,
                    )

                    temp_path = Path(temp_file.name)

                documents = ingestion_service.ingest(
                    temp_path,
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

    except Exception:
        raise



@router.get(
    "",
    response_model=list[StandardDocumentResponse],
)
def get_workspace_documents(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[StandardDocumentResponse]:
    document_service = StandardDocumentService(db)

    documents = document_service.get_workspace_documents_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if documents is None:
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
