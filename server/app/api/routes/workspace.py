from app.auth.current_user import get_current_db_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
)
from app.services.workspace_service import WorkspaceService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from uuid import UUID

router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace_service = WorkspaceService(db)

    workspace = workspace_service.create_workspace(
        user_id=current_user.id,
        name=workspace_data.name,
        description=workspace_data.description,
    )

    return WorkspaceResponse(
        id=workspace.id,
        user_id=workspace.user_id,
        name=workspace.name,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.get(
    "",
    response_model=list[WorkspaceResponse],
)
def get_workspaces(
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    workspace_service = WorkspaceService(db)

    workspaces = workspace_service.get_workspaces_for_user(
        current_user.id,
    )

    return [
        WorkspaceResponse(
            id=workspace.id,
            user_id=workspace.user_id,
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        for workspace in workspaces
    ]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace_service = WorkspaceService(db)

    workspace = workspace_service.get_workspace(
        workspace_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    if workspace.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return WorkspaceResponse(
        id=workspace.id,
        user_id=workspace.user_id,
        name=workspace.name,
        description=workspace.description,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )




@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> None:
    workspace_service = WorkspaceService(db)

    workspace = workspace_service.get_workspace(
        workspace_id,
    )

    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    if workspace.user_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    workspace_service.delete_workspace(
        workspace,
    )
