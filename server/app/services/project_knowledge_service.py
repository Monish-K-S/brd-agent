from dataclasses import asdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.consolidators.knowledge_consolidator import (
    KnowledgeConsolidator,
)
from app.ai.mappers.document_knowledge_mapper import (
    DocumentKnowledgeMapper,
)
from app.db.models.project_knowledge import ProjectKnowledge
from app.repositories.document_extraction_repository import (
    DocumentExtractionRepository,
)
from app.repositories.project_knowledge_repository import (
    ProjectKnowledgeRepository,
)
from app.services.workspace_service import WorkspaceService


class ProjectKnowledgeService:
    def __init__(self, db: Session):
        self.db = db

        self.project_knowledge_repository = (
            ProjectKnowledgeRepository(db)
        )

        self.document_extraction_repository = (
            DocumentExtractionRepository(db)
        )

        self.workspace_service = WorkspaceService(db)

        self.document_knowledge_mapper = (
            DocumentKnowledgeMapper()
        )

        self.knowledge_consolidator = (
            KnowledgeConsolidator()
        )

    def get_project_knowledge_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ProjectKnowledge | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        return self.project_knowledge_repository.get_by_workspace_id(
            workspace_id,
        )

    def consolidate_project_knowledge(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ProjectKnowledge | None:
        """
        Consolidate all DocumentExtraction knowledge in a workspace
        into a single ProjectKnowledge record.
        """

        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        extractions = (
            self.document_extraction_repository
            .get_all_by_workspace_id(
                workspace_id,
            )
        )

        if not extractions:
            return None

        document_knowledge_list = [
            self.document_knowledge_mapper.map(
                extraction.document_knowledge,
            )
            for extraction in extractions
        ]

        project_knowledge = (
            self.knowledge_consolidator.consolidate(
                document_knowledge_list,
            )
        )

        knowledge_data = asdict(
            project_knowledge,
        )

        return self.save_project_knowledge(
            workspace_id=workspace_id,
            user_id=user_id,
            knowledge_data=knowledge_data,
        )

    def save_project_knowledge(
        self,
        workspace_id: UUID,
        user_id: UUID,
        knowledge_data: dict,
    ) -> ProjectKnowledge | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        existing_project_knowledge = (
            self.project_knowledge_repository.get_by_workspace_id(
                workspace_id,
            )
        )

        try:
            if existing_project_knowledge is None:
                project_knowledge = ProjectKnowledge(
                    workspace_id=workspace_id,
                    knowledge_data=knowledge_data,
                )

                saved_project_knowledge = (
                    self.project_knowledge_repository.create(
                        project_knowledge,
                    )
                )
            else:
                existing_project_knowledge.knowledge_data = (
                    knowledge_data
                )

                saved_project_knowledge = (
                    self.project_knowledge_repository.update(
                        existing_project_knowledge,
                    )
                )

            self.db.commit()

            self.db.refresh(
                saved_project_knowledge,
            )

            return saved_project_knowledge

        except Exception:
            self.db.rollback()
            raise
