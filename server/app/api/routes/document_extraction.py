from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_db_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document_extraction import (
    DocumentExtractionResponse,
)
from app.services.document_extraction_service import (
    DocumentExtractionService,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/extractions",
    tags=["Document Extractions"],
)


@router.post(
    "",
    response_model=DocumentExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.rate_limit_extract)
def extract_documents(
    request: Request,
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> DocumentExtractionResponse:
    extraction_service = DocumentExtractionService(
        db,
    )

    extraction = extraction_service.extract_workspace_documents(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if extraction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Workspace not found or no unextracted "
                "documents available"
            ),
        )

    return DocumentExtractionResponse(
        id=extraction.id,
        workspace_id=extraction.workspace_id,
        document_knowledge=extraction.document_knowledge,
        created_at=extraction.created_at,
        updated_at=extraction.updated_at,
    )
