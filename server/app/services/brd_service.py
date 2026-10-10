from datetime import datetime, timezone
import tempfile
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.builders.brd_document_builder import BRDDocumentBuilder
from app.ai.builders.brd_docx_builder import BRDDocxBuilder
from app.ai.generators.gemini_brd_generator import (
    GeminiBRDGenerator,
)
from app.ai.mappers.brd_mapper import BRDMapper
from app.ai.mappers.project_knowledge_mapper import (
    ProjectKnowledgeMapper,
)
from app.db.models.brd import BRD
from app.repositories.brd_repository import BRDRepository
from app.repositories.generation_job_repository import (
    GenerationJobRepository,
)
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.schemas.brd import BRDMalformedError
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)
from app.services.workspace_service import WorkspaceService


class BRDService:
    def __init__(self, db: Session):
        self.db = db

        self.brd_repository = BRDRepository(db)
        self.standard_document_repository = StandardDocumentRepository(db)

        self.generation_job_repository = GenerationJobRepository(db)

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

        self.brd_document_builder = BRDDocumentBuilder()
        self.brd_docx_builder = BRDDocxBuilder()

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

    def update_brd_for_user(
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

        brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        if brd is None:
            return None

        try:
            brd.brd_data = brd_data
            brd.user_edited_at = datetime.now(timezone.utc)

            saved_brd = self.brd_repository.update(
                brd,
            )

            self.db.commit()

            return saved_brd

        except Exception:
            self.db.rollback()
            raise

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

    def export_brd_pdf_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> tuple[str, str] | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        if brd is None:
            return None

        try:
            brd_model = self.brd_mapper.map(
                brd.brd_data,
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise BRDMalformedError(
                "Stored BRD data is malformed and cannot be exported. "
                "Regenerate the BRD to fix this."
            ) from exc

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        )

        temp_file.close()

        output_path = temp_file.name

        try:
            self.brd_document_builder.build(
                brd=brd_model,
                output_path=output_path,
            )
        except Exception:
            Path(output_path).unlink(
                missing_ok=True,
            )
            raise

        return output_path, workspace.name

    def export_brd_docx_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> tuple[str, str] | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        if brd is None:
            return None

        try:
            brd_model = self.brd_mapper.map(
                brd.brd_data,
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise BRDMalformedError(
                "Stored BRD data is malformed and cannot be exported. "
                "Regenerate the BRD to fix this."
            ) from exc

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".docx",
            delete=False,
        )

        temp_file.close()

        output_path = temp_file.name

        try:
            self.brd_docx_builder.build(
                brd=brd_model,
                output_path=output_path,
            )
        except Exception:
            Path(output_path).unlink(
                missing_ok=True,
            )
            raise

        return output_path, workspace.name

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
                    source_revision=workspace.source_revision,
                )

                saved_brd = self.brd_repository.create(
                    brd,
                )
            else:
                existing_brd.brd_data = brd_data
                existing_brd.source_revision = workspace.source_revision
                existing_brd.user_edited_at = None

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

        has_sources = (
            self.standard_document_repository.has_by_workspace_id(
                workspace_id,
            )
        )

        has_new_sources = (
            self.standard_document_repository.has_unextracted_by_workspace_id(
                workspace_id,
            )
        )

        has_brd = brd is not None

        if not has_brd:
            regeneration_required = False
        else:
            regeneration_required = (
                brd.source_revision
                != workspace.source_revision
            )

        has_user_edits = (
            brd is not None
            and brd.user_edited_at is not None
        )

        active_job = (
            self.generation_job_repository.get_active_by_workspace_id(
                workspace_id,
            )
        )

        latest_job = (
            self.generation_job_repository.get_latest_by_workspace_id(
                workspace_id,
            )
        )

        def serialize_job(job):
            return {
                "job_id": job.id,
                "status": job.status,
                "phase": job.phase,
                "error": job.error,
            }

        return {
            "has_brd": has_brd,
            "has_sources": has_sources,
            "has_new_sources": has_new_sources,
            "regeneration_required": regeneration_required,
            "has_user_edits": has_user_edits,
            "active_job": (
                serialize_job(active_job)
                if active_job is not None
                else None
            ),
            "last_job": (
                serialize_job(latest_job)
                if latest_job is not None
                else None
            ),
        }
