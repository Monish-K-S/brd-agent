import tempfile
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.builders.project_document_builder import (
    ProjectDocumentBuilder,
)
from app.ai.extractors.sarvam_extractor import SarvamExtractor
from app.ai.extractors.sarvam_knowledge_mapper import (
    SarvamKnowledgeMapper,
)
from app.ai.models.standard_document import (
    StandardDocument as AIStandardDocument,
)
from app.core.config import settings
from app.db.models.document_extraction import DocumentExtraction
from app.db.models.standard_document import (
    StandardDocument as DBStandardDocument,
)
from app.db.models.workspace import Workspace
from app.repositories.document_extraction_repository import (
    DocumentExtractionRepository,
)
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.repositories.workspace_repository import (
    WorkspaceRepository,
)


class DocumentExtractionService:
    # Appended to the last document when the aggregate budget cuts it off,
    # so the omission is visible in the generated project PDF.
    TRUNCATION_MARKER = (
        "\n\n[Content truncated to fit the extraction budget.]"
    )

    def __init__(self, db: Session):
        self.db = db

        self.workspace_repository = WorkspaceRepository(db)

        self.standard_document_repository = StandardDocumentRepository(db)

        self.document_extraction_repository = DocumentExtractionRepository(db)

        self.document_builder = ProjectDocumentBuilder()

        self.sarvam_extractor = SarvamExtractor(
            schema_path=(
                Path(__file__).resolve().parent.parent
                / "ai"
                / "schemas"
                / "document_knowledge_schema.json"
            ),
        )

        self.knowledge_mapper = SarvamKnowledgeMapper()

    def extract_workspace_documents(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> DocumentExtraction | None:
        """
        Extract knowledge from all unextracted documents
        in a workspace.
        """

        workspace = self._get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        documents = self.standard_document_repository.get_unextracted_by_workspace_id(
            workspace_id,
        )

        if not documents:
            return None

        ai_documents = [
            self._convert_to_ai_document(
                document,
            )
            for document in documents
        ]

        # Per-document caps leave the aggregate unbounded (N docs x
        # 500k chars), so bound what actually goes to Sarvam (M-2).
        ai_documents = self._fit_to_aggregate_budget(
            ai_documents,
        )

        included_ids = {
            document.id
            for document in ai_documents
        }

        if not included_ids:
            return None

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            self.document_builder.build(
                documents=ai_documents,
                output_path=str(temp_path),
            )

            raw_sarvam_response = self.sarvam_extractor.extract(
                pdf_path=temp_path,
            )

            document_knowledge = self.knowledge_mapper.map(
                raw_sarvam_response,
            )

            knowledge_data = asdict(
                document_knowledge,
            )

            extraction = DocumentExtraction(
                workspace_id=workspace_id,
                document_knowledge=knowledge_data,
                raw_sarvam_response=raw_sarvam_response,
            )

            try:
                created_extraction = self.document_extraction_repository.create(
                    extraction,
                )

                self.document_extraction_repository.link_source_documents(
                    extraction_id=created_extraction.id,
                    document_ids=sorted(included_ids),
                )

                # Mark only what was actually fed to Sarvam. Documents
                # dropped by the budget stay unextracted and are picked up
                # by a later run once the budget frees up.
                for document in documents:
                    if document.id in included_ids:
                        document.is_extracted = True

                self.db.commit()

                self.db.refresh(
                    created_extraction,
                )

                return created_extraction

            except Exception:
                self.db.rollback()
                raise

        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def _get_workspace_for_user(
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

    @staticmethod
    def _convert_to_ai_document(
        document: DBStandardDocument,
    ) -> AIStandardDocument:
        return AIStandardDocument(
            id=document.id,
            source_type=document.source_type,
            title=document.title,
            author=document.author,
            source_created_at=document.source_created_at,
            participants=document.participants,
            content=document.content,
            metadata=document.metadata_,
        )

    def _fit_to_aggregate_budget(
        self,
        documents: list[AIStandardDocument],
    ) -> list[AIStandardDocument]:
        """
        Bound the total content handed to the project PDF builder.

        Documents are included in order until the budget is exhausted.
        The one that crosses the boundary is truncated with an explicit
        marker; anything after it is dropped from this run so it remains
        unextracted for a later pass.
        """

        budget = settings.max_aggregate_chars
        total = 0
        fitted: list[AIStandardDocument] = []

        for document in documents:
            remaining = budget - total

            if remaining <= 0:
                break

            content = document.content

            if len(content) > remaining:
                document.content = (
                    content[:remaining] + self.TRUNCATION_MARKER
                )

            total += len(document.content)
            fitted.append(document)

        return fitted
