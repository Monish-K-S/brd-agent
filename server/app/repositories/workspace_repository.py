from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.workspace import Workspace


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        workspace_id: UUID,
    ) -> Workspace | None:
        return self.db.get(
            Workspace,
            workspace_id,
        )

    def get_by_user_id_and_name(
        self,
        user_id: UUID,
        name: str,
    ) -> Workspace | None:
        return (
            self.db.query(Workspace)
            .filter(
                Workspace.user_id == user_id,
                func.lower(Workspace.name) == name.lower(),
            )
            .first()
        )


    def create(
        self,
        workspace: Workspace,
    ) -> Workspace:
        self.db.add(workspace)
        self.db.flush()
        self.db.refresh(workspace)

        return workspace

    def get_all_by_user_id(
        self,
        user_id: UUID,
    ) -> list[Workspace]:
        return (
            self.db.query(Workspace)
            .filter(Workspace.user_id == user_id)
            .order_by(Workspace.created_at.desc())
            .all()
        )

    def delete(
        self,
        workspace: Workspace,
    ) -> None:
        self.db.delete(workspace)
        self.db.flush()
