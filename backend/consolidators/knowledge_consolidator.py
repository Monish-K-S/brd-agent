from models.knowledge.document_knowledge import DocumentKnowledge
from models.knowledge.project_knowledge import ProjectKnowledge


class KnowledgeConsolidator:
    """
    Consolidates document-level knowledge into project-level knowledge.
    """

    def consolidate(
        self,
        documents: list[DocumentKnowledge],
    ) -> ProjectKnowledge:
        if not documents:
            return ProjectKnowledge()

        if len(documents) == 1:
            return self._from_single_document(documents[0])

        return self._merge_documents(documents)

    @staticmethod
    def _from_single_document(
        document: DocumentKnowledge,
    ) -> ProjectKnowledge:
        return ProjectKnowledge(
            project_metadata=document.project_metadata,
            stakeholders=list(document.stakeholders),
            business_objectives=list(document.business_objectives),
            functional_requirements=list(
                document.functional_requirements
            ),
            non_functional_requirements=list(
                document.non_functional_requirements
            ),
            assumptions=list(document.assumptions),
            constraints=list(document.constraints),
            risks=list(document.risks),
            decisions=list(document.decisions),
            out_of_scope=list(document.out_of_scope),
            open_questions=list(document.open_questions),
        )

    def _merge_documents(
        self,
        documents: list[DocumentKnowledge],
    ) -> ProjectKnowledge:
        """
        Temporary deterministic merge for multiple
        DocumentKnowledge objects.

        No deduplication or conflict resolution is performed yet.
        """

        project = ProjectKnowledge()

        for document in documents:
            if project.project_metadata is None:
                project.project_metadata = document.project_metadata

            project.stakeholders.extend(
                document.stakeholders
            )

            project.business_objectives.extend(
                document.business_objectives
            )

            project.functional_requirements.extend(
                document.functional_requirements
            )

            project.non_functional_requirements.extend(
                document.non_functional_requirements
            )

            project.assumptions.extend(
                document.assumptions
            )

            project.constraints.extend(
                document.constraints
            )

            project.risks.extend(
                document.risks
            )

            project.decisions.extend(
                document.decisions
            )

            project.out_of_scope.extend(
                document.out_of_scope
            )

            project.open_questions.extend(
                document.open_questions
            )

        return project
