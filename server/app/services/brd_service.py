from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.generators.gemini_brd_generator import (
    GeminiBRDGenerator,
)
from app.ai.mappers.brd_mapper import BRDMapper
from app.ai.mappers.project_knowledge_mapper import (
    ProjectKnowledgeMapper,
)
from app.db.models.brd import BRD
from app.repositories.brd_repository import BRDRepository
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)
from app.services.workspace_service import WorkspaceService


class BRDService:
    def __init__(self, db: Session):
        self.db = db

        self.brd_repository = BRDRepository(db)
        self.standard_document_repository = StandardDocumentRepository(db)

        self.workspace_service = WorkspaceService(db)

        self.project_knowledge_service = ProjectKnowledgeService(db)

        self.project_knowledge_mapper = ProjectKnowledgeMapper()

        self.brd_mapper = BRDMapper()

        self.brd_generator = GeminiBRDGenerator(
            schema_path=(
                Path(__file__).resolve().parent.parent
                / "ai"
                / "schemas"
                / "brd_schema.json"
            ),
        )

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

    def generate_brd_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> BRD | None:
        """
        Generate a BRD from the workspace ProjectKnowledge.
        """

        project_knowledge_record = (
            self.project_knowledge_service.get_project_knowledge_for_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )
        )

        if project_knowledge_record is None:
            return None

        project_knowledge = self.project_knowledge_mapper.map(
            project_knowledge_record.knowledge_data,
        )

        generated_brd_data = self.brd_generator.generate(
            project_knowledge,
        )

        brd = self.brd_mapper.map(
            generated_brd_data,
        )

        brd_data = asdict(
            brd,
        )

        return self.save_brd(
            workspace_id=workspace_id,
            user_id=user_id,
            brd_data=brd_data,
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



    def get_brd_status_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
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

        has_new_sources = (
            self.standard_document_repository
            .has_unextracted_by_workspace_id(
                workspace_id,
            )
        )

        has_brd = brd is not None

        return {
            "has_brd": has_brd,
            "has_new_sources": has_new_sources,
            "regeneration_required": (
                has_brd and has_new_sources
            ),
        }
