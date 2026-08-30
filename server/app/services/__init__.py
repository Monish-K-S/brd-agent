from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.workspace import Workspace
from app.repositories.workspace_repository import (
    WorkspaceRepository,
)


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.workspace_repository = WorkspaceRepository(db)


    def create_workspace(
        self,
        user_id: UUID,
        name: str,
        description: str | None = None,
    ) -> Workspace:
        workspace = Workspace(
            user_id=user_id,
            name=name,
            description=description,
        )

        created_workspace = self.workspace_repository.create(
            workspace,
        )

        self.db.commit()

        return created_workspace


    def get_workspace(
        self,
        workspace_id: UUID,
    ) -> Workspace | None:
        return self.workspace_repository.get_by_id(
            workspace_id,
        )


    def get_user_workspaces(
        self,
        user_id: UUID,
    ) -> list[Workspace]:
        return self.workspace_repository.get_all_by_user_id(
            user_id,
        )


    def get_workspace_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Workspace | None:
        workspace = self.workspace_repository.get_by_id(
            workspace_id,
        )

        if workspace is None:
            return None

        if workspace.user_id != user_id:
            return None

        return workspace




    def delete_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        workspace = self.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return False

        self.workspace_repository.delete(workspace)

        self.db.commit()

        return True
