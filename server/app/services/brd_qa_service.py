from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.generators.gemini_brd_qa_generator import (
    GeminiBRDQAGenerator,
)
from app.db.models.standard_document import StandardDocument
from app.repositories.brd_repository import BRDRepository
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)
from app.services.workspace_service import WorkspaceService


class BRDQAService:
    def __init__(self, db: Session):
        self.db = db

        self.brd_repository = BRDRepository(db)

        self.standard_document_repository = StandardDocumentRepository(db)

        self.project_knowledge_service = ProjectKnowledgeService(db)

        self.workspace_service = WorkspaceService(db)

        self.qa_generator = GeminiBRDQAGenerator()

    def answer_question_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        question: str,
    ) -> dict | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        project_knowledge = (
            self.project_knowledge_service.get_project_knowledge_for_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )
        )

        if brd is None and project_knowledge is None:
            return {
                "answer": (
                    "There is no BRD or project knowledge available "
                    "for this workspace yet."
                ),
                "sources": [],
            }

        source_documents = self.standard_document_repository.get_all_by_workspace_id(
            workspace_id,
        )

        brd_data = brd.brd_data if brd is not None else {}

        project_knowledge_data = (
            project_knowledge.knowledge_data if project_knowledge is not None else {}
        )

        source_context = [
            self._serialize_source_document(
                document,
            )
            for document in source_documents
        ]

        generated_response = self.qa_generator.answer(
            question=question,
            brd_data=brd_data,
            project_knowledge=project_knowledge_data,
            source_documents=source_context,
        )

        valid_source_ids = self._validate_source_ids(
            source_documents=source_documents,
            source_ids=generated_response["source_ids"],
        )

        sources = [
            self._serialize_source_reference(
                document,
            )
            for document in source_documents
            if str(document.id) in valid_source_ids
        ]

        return {
            "answer": generated_response["answer"],
            "sources": sources,
        }

    @staticmethod
    def _serialize_source_document(
        document: StandardDocument,
    ) -> dict:
        return {
            "id": str(document.id),
            "title": document.title,
            "source_type": document.source_type,
            "author": document.author,
            "source_created_at": (
                document.source_created_at.isoformat()
                if document.source_created_at
                else None
            ),
            "participants": document.participants,
            "content": document.content,
        }

    @staticmethod
    def _serialize_source_reference(
        document: StandardDocument,
    ) -> dict:
        return {
            "id": document.id,
            "title": document.title,
            "source_type": document.source_type,
        }

    @staticmethod
    def _validate_source_ids(
        source_documents: list[StandardDocument],
        source_ids: list[str],
    ) -> set[str]:
        available_ids = {str(document.id) for document in source_documents}

        return {source_id for source_id in source_ids if source_id in available_ids}
