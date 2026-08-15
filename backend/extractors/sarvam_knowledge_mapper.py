from models.knowledge.document_knowledge import DocumentKnowledge
from models.knowledge.functional_requirement import FunctionalRequirement
from models.knowledge.non_functional_requirement import NonFunctionalRequirement
from models.knowledge.project_metadata import ProjectMetadata
from models.knowledge.stakeholder import Stakeholder


class SarvamKnowledgeMapper:
    """
    Maps the `result` section of a Sarvam Document AI
    response into a DocumentKnowledge object.
    """

    def map(
        self,
        sarvam_response: dict,
    ) -> DocumentKnowledge:
        result = sarvam_response.get("result", {})

        return DocumentKnowledge(
            project_metadata=self._map_project_metadata(result.get("project_metadata")),
            stakeholders=self._map_stakeholders(result.get("stakeholders", [])),
            business_objectives=result.get(
                "business_objectives",
                [],
            ),
            functional_requirements=self._map_functional_requirements(
                result.get("functional_requirements", [])
            ),
            non_functional_requirements=self._map_non_functional_requirements(
                result.get(
                    "non_functional_requirements",
                    [],
                )
            ),
            assumptions=result.get(
                "assumptions",
                [],
            ),
            constraints=result.get(
                "constraints",
                [],
            ),
            risks=result.get(
                "risks",
                [],
            ),
            decisions=result.get(
                "decisions",
                [],
            ),
            out_of_scope=result.get(
                "out_of_scope",
                [],
            ),
            open_questions=result.get(
                "open_questions",
                [],
            ),
        )

    @staticmethod
    def _map_project_metadata(
        data: dict | None,
    ) -> ProjectMetadata | None:
        if not data:
            return None

        return ProjectMetadata(
            project_name=data.get("project_name"),
            description=data.get("description"),
        )

    @staticmethod
    def _map_stakeholders(
        stakeholders: list[dict],
    ) -> list[Stakeholder]:
        return [
            Stakeholder(
                name=stakeholder.get("name", ""),
                role=stakeholder.get("role"),
                organization=stakeholder.get("organization"),
            )
            for stakeholder in stakeholders
        ]

    @staticmethod
    def _map_functional_requirements(
        requirements: list[str],
    ) -> list[FunctionalRequirement]:
        return [
            FunctionalRequirement(
                description=requirement,
            )
            for requirement in requirements
        ]

    @staticmethod
    def _map_non_functional_requirements(
        requirements: list[dict],
    ) -> list[NonFunctionalRequirement]:
        return [
            NonFunctionalRequirement(
                category=requirement.get(
                    "category",
                    "",
                ),
                description=requirement.get(
                    "description",
                    "",
                ),
            )
            for requirement in requirements
        ]
