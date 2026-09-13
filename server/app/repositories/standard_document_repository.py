from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.standard_document import StandardDocument


class StandardDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        document_id: UUID,
    ) -> StandardDocument | None:
        return self.db.get(
            StandardDocument,
            document_id,
        )

    def get_all_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> list[StandardDocument]:
        return (
            self.db.query(StandardDocument)
            .filter(
                StandardDocument.workspace_id == workspace_id,
            )
            .order_by(
                StandardDocument.created_at.asc(),
            )
            .all()
        )

    def get_unextracted_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> list[StandardDocument]:
        return (
            self.db.query(StandardDocument)
            .filter(
                StandardDocument.workspace_id == workspace_id,
                StandardDocument.is_extracted.is_(False),
            )
            .order_by(
                StandardDocument.created_at.asc(),
            )
            .all()
        )

    def create(
        self,
        document: StandardDocument,
    ) -> StandardDocument:
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)

        return document

    def create_many(
        self,
        documents: list[StandardDocument],
    ) -> list[StandardDocument]:
        self.db.add_all(documents)
        self.db.flush()

        for document in documents:
            self.db.refresh(document)

        return documents

    def delete(
        self,
        document: StandardDocument,
    ) -> None:
        self.db.delete(document)
        self.db.flush()

    def has_unextracted_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> bool:
        return (
            self.db.query(StandardDocument)
            .filter(
                StandardDocument.workspace_id == workspace_id,
                StandardDocument.is_extracted.is_(False),
            )
            .first()
            is not None
        )

    def has_by_workspace_id(
        self,
        workspace_id: UUID,
    ) -> bool:
        return (
            self.db.query(StandardDocument)
            .filter(
                StandardDocument.workspace_id == workspace_id,
            )
            .first()
            is not None
        )

    def get_by_gmail_message_id(
        self,
        workspace_id: UUID,
        gmail_message_id: str,
    ) -> StandardDocument | None:
        return (
            self.db.query(StandardDocument)
            .filter(
                StandardDocument.workspace_id == workspace_id,
                StandardDocument.metadata_["gmail_message_id"].astext
                == gmail_message_id,
            )
            .first()
        )
