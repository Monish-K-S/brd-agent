from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.brd import BRD
from app.repositories.brd_repository import BRDRepository
from app.services.workspace_service import WorkspaceService


class BRDService:
    def __init__(self, db: Session):
        self.db = db

        self.brd_repository = BRDRepository(db)

        self.workspace_service = WorkspaceService(db)




    def get_brd_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> BRD | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return self.brd_repository.get_by_workspace_id(
            workspace_id,
        )



    def save_brd(
        self,
        workspace_id: UUID,
        user_id: UUID,
        brd_data: dict,
    ) -> BRD | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        existing_brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        try:
            if existing_brd is None:
                brd = BRD(
                    workspace_id=workspace_id,
                    brd_data=brd_data,
                )

                saved_brd = self.brd_repository.create(
                    brd,
                )
            else:
                existing_brd.brd_data = brd_data

                saved_brd = self.brd_repository.update(
                    existing_brd,
                )

            self.db.commit()

            return saved_brd

        except Exception:
            self.db.rollback()
            raise
