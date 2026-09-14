from pathlib import Path
from uuid import UUID

from app.auth.current_user import get_current_db_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.brd import (
    BRDResponse,
    BRDStatusResponse,
    BRDUpdateRequest,
)
from app.services.brd_service import BRDService
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask


def _cleanup_export_file(path: str) -> None:
    Path(path).unlink(missing_ok=True)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/brd",
    tags=["BRD"],
)


@router.post(
    "/generate",
    response_model=BRDResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_brd(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> BRDResponse:
    brd_service = BRDService(db)

    brd = brd_service.generate_brd_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if brd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("Workspace not found or project knowledge not available"),
        )

    return BRDResponse(
        id=brd.id,
        workspace_id=brd.workspace_id,
        brd_data=brd.brd_data,
        created_at=brd.created_at,
        updated_at=brd.updated_at,
        user_edited_at=brd.user_edited_at,
    )


@router.get(
    "/status",
    response_model=BRDStatusResponse,
)
def get_brd_status(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> BRDStatusResponse:
    brd_service = BRDService(db)

    brd_status = brd_service.get_brd_status_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if brd_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    return BRDStatusResponse(
        has_brd=brd_status["has_brd"],
        has_sources=brd_status["has_sources"],
        has_new_sources=brd_status["has_new_sources"],
        regeneration_required=brd_status["regeneration_required"],
        has_user_edits=brd_status["has_user_edits"],
    )


@router.get(
    "",
    response_model=BRDResponse,
)
def get_brd(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> BRDResponse:
    brd_service = BRDService(db)

    brd = brd_service.get_brd_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if brd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BRD not found",
        )

    return BRDResponse(
        id=brd.id,
        workspace_id=brd.workspace_id,
        brd_data=brd.brd_data,
        created_at=brd.created_at,
        updated_at=brd.updated_at,
        user_edited_at=brd.user_edited_at,
    )


@router.put(
    "",
    response_model=BRDResponse,
)
def update_brd(
    workspace_id: UUID,
    request: BRDUpdateRequest,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> BRDResponse:
    brd_service = BRDService(db)

    brd = brd_service.update_brd_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
        brd_data=request.brd_data,
    )

    if brd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BRD not found",
        )

    return BRDResponse(
        id=brd.id,
        workspace_id=brd.workspace_id,
        brd_data=brd.brd_data,
        created_at=brd.created_at,
        updated_at=brd.updated_at,
        user_edited_at=brd.user_edited_at,
    )


@router.get("/export/pdf")
def export_brd_pdf(
    workspace_id: UUID,
    current_user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    brd_service = BRDService(db)

    result = brd_service.export_brd_pdf_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BRD not found",
        )

    output_path, workspace_name = result

    filename = f"{workspace_name.strip() or 'BRD'} - BRD.pdf"

    return FileResponse(
        path=output_path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(
            _cleanup_export_file,
            output_path,
        ),
    )


@router.get("/export/docx")
def export_brd_docx(
    workspace_id: UUID,
    current_user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    brd_service = BRDService(db)

    result = brd_service.export_brd_docx_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BRD not found",
        )

    output_path, workspace_name = result

    filename = f"{workspace_name.strip() or 'BRD'} - BRD.docx"

    return FileResponse(
        path=output_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=filename,
        background=BackgroundTask(
            _cleanup_export_file,
            output_path,
        ),
    )
