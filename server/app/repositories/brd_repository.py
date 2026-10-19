from uuid import UUID

from sqlalchemy.orm import Session, defer

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

    def get_summary_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> BRD | None:
        """Row without ``brd_data`` (the full 11-section document JSON).

        The status endpoint runs every 2s while a job is tracked and only
        reads existence, ``source_revision`` and ``user_edited_at`` — no
        reason to ship the document itself over the wire each poll (P-4).
        Anything that renders or exports the BRD keeps using
        ``get_by_workspace_id``.
        """
        return (
            self.db.query(BRD)
            .options(defer(BRD.brd_data))
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
