import json
from dataclasses import asdict, is_dataclass

from app.ai.models.knowledge.document_knowledge import (
    DocumentKnowledge,
)
from app.ai.models.knowledge.project_knowledge import (
    ProjectKnowledge,
)


class KnowledgeConsolidator:
    """
    Consolidates document-level knowledge into project-level knowledge.
    """

    # Every list field shared by DocumentKnowledge and ProjectKnowledge.
    # Driving both paths from one tuple means a new field cannot silently
    # skip deduplication.
    _LIST_FIELDS = (
        "stakeholders",
        "business_objectives",
        "functional_requirements",
        "non_functional_requirements",
        "assumptions",
        "constraints",
        "risks",
        "decisions",
        "out_of_scope",
        "open_questions",
    )

    def consolidate(
        self,
        documents: list[DocumentKnowledge],
    ) -> ProjectKnowledge:
        if not documents:
            return ProjectKnowledge()

        if len(documents) == 1:
            return self._from_single_document(
                documents[0],
            )

        return self._merge_documents(
            documents,
        )

    @staticmethod
    def _from_single_document(
        document: DocumentKnowledge,
    ) -> ProjectKnowledge:
        return ProjectKnowledge(
            project_metadata=document.project_metadata,
            **{
                field_name: KnowledgeConsolidator._dedupe(
                    list(getattr(document, field_name)),
                )
                for field_name in KnowledgeConsolidator._LIST_FIELDS
            },
        )

    @staticmethod
    def _canonical_key(item: object) -> str:
        """Stable identity for one knowledge item.

        Only used to drop exact repeats, so normalization is limited to
        whitespace collapsing and case — never digits or punctuation.
        Requirements that differ in a threshold ("3.5 seconds" vs
        "35 seconds") therefore cannot collide.
        """
        payload = (
            asdict(item)
            if is_dataclass(item) and not isinstance(item, type)
            else item
        )

        return json.dumps(
            KnowledgeConsolidator._normalize(payload),
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _normalize(value: object) -> object:
        if isinstance(value, str):
            return " ".join(value.split()).lower()

        if isinstance(value, dict):
            return {
                key: KnowledgeConsolidator._normalize(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                KnowledgeConsolidator._normalize(item)
                for item in value
            ]

        return value

    @staticmethod
    def _dedupe(items: list) -> list:
        """Drop identical repeats, keeping first-seen order.

        Workspaces built from several documents routinely state the same
        requirement once per document: measured 147 items of which only 70
        were distinct (52% removable) on a real 9-document workspace. The
        BRD call was paying Gemini to reconcile those, so removing them
        here cuts prompt size and hidden thinking time without touching
        any semantic judgement.

        Near-duplicates are deliberately **kept** — deciding whether two
        differently-worded requirements are the same is exactly the
        judgement left to the BRD generation step.
        """
        seen: set[str] = set()
        kept: list = []

        for item in items:
            key = KnowledgeConsolidator._canonical_key(item)

            if key in seen:
                continue

            seen.add(key)
            kept.append(item)

        return kept

    def _merge_documents(
        self,
        documents: list[DocumentKnowledge],
    ) -> ProjectKnowledge:
        """
        Deterministically merges multiple DocumentKnowledge
        objects into a ProjectKnowledge object.

        Exact duplicates are dropped (see ``_dedupe``). Semantic
        near-duplicates and conflicts are deliberately *not* resolved
        here — that judgement stays with the BRD generation step.
        """

        project = ProjectKnowledge()

        for document in documents:
            if project.project_metadata is None:
                project.project_metadata = (
                    document.project_metadata
                )

            project.stakeholders.extend(
                document.stakeholders,
            )

            project.business_objectives.extend(
                document.business_objectives,
            )

            project.functional_requirements.extend(
                document.functional_requirements,
            )

            project.non_functional_requirements.extend(
                document.non_functional_requirements,
            )

            project.assumptions.extend(
                document.assumptions,
            )

            project.constraints.extend(
                document.constraints,
            )

            project.risks.extend(
                document.risks,
            )

            project.decisions.extend(
                document.decisions,
            )

            project.out_of_scope.extend(
                document.out_of_scope,
            )

            project.open_questions.extend(
                document.open_questions,
            )

        for field_name in KnowledgeConsolidator._LIST_FIELDS:
            setattr(
                project,
                field_name,
                KnowledgeConsolidator._dedupe(
                    getattr(project, field_name),
                ),
            )

        return project
