from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.current_user import get_current_db_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.brd import BRDResponse
from app.services.brd_service import BRDService


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
            detail=(
                "Workspace not found or project knowledge "
                "not available"
            ),
        )

    return BRDResponse(
        id=brd.id,
        workspace_id=brd.workspace_id,
        brd_data=brd.brd_data,
        created_at=brd.created_at,
        updated_at=brd.updated_at,
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
    )
