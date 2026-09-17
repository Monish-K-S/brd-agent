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
from app.schemas.project_knowledge import (
    ProjectKnowledgeResponse,
)
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)


router = APIRouter(
    prefix="/workspaces/{workspace_id}/project-knowledge",
    tags=["Project Knowledge"],
)


@router.post(
    "/consolidate",
    response_model=ProjectKnowledgeResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_consolidate)
def consolidate_project_knowledge(
    request: Request,
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> ProjectKnowledgeResponse:
    project_knowledge_service = ProjectKnowledgeService(
        db,
    )

    project_knowledge = (
        project_knowledge_service.consolidate_project_knowledge(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    )

    if project_knowledge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Workspace not found or no document "
                "extractions available"
            ),
        )

    return ProjectKnowledgeResponse(
        id=project_knowledge.id,
        workspace_id=project_knowledge.workspace_id,
        knowledge_data=project_knowledge.knowledge_data,
        created_at=project_knowledge.created_at,
        updated_at=project_knowledge.updated_at,
    )


@router.get(
    "",
    response_model=ProjectKnowledgeResponse,
)
def get_project_knowledge(
    workspace_id: UUID,
    current_user: User = Depends(
        get_current_db_user,
    ),
    db: Session = Depends(get_db),
) -> ProjectKnowledgeResponse:
    project_knowledge_service = ProjectKnowledgeService(
        db,
    )

    project_knowledge = (
        project_knowledge_service.get_project_knowledge_for_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
    )

    if project_knowledge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project knowledge not found",
        )

    return ProjectKnowledgeResponse(
        id=project_knowledge.id,
        workspace_id=project_knowledge.workspace_id,
        knowledge_data=project_knowledge.knowledge_data,
        created_at=project_knowledge.created_at,
        updated_at=project_knowledge.updated_at,
    )
