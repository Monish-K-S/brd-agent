from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.brd import BRD


class BRDRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> BRD | None:
        return (
            self.db.query(BRD)
            .filter(
                BRD.workspace_id == workspace_id,
            )
            .first()
        )

    def create(
        self,
        brd: BRD,
    ) -> BRD:
        self.db.add(brd)
        self.db.flush()
        self.db.refresh(brd)

        return brd

    def update(
        self,
        brd: BRD,
    ) -> BRD:
        self.db.flush()
        self.db.refresh(brd)

        return brd
