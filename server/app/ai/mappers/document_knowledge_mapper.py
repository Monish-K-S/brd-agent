from app.ai.models.knowledge.assumption import Assumption
from app.ai.models.knowledge.business_objective import (
    BusinessObjective,
)
from app.ai.models.knowledge.constraint import Constraint
from app.ai.models.knowledge.decision import Decision
from app.ai.models.knowledge.document_knowledge import (
    DocumentKnowledge,
)
from app.ai.models.knowledge.functional_requirement import (
    FunctionalRequirement,
)
from app.ai.models.knowledge.non_functional_requirement import (
    NonFunctionalRequirement,
)
from app.ai.models.knowledge.open_question import OpenQuestion
from app.ai.models.knowledge.out_of_scope import OutOfScope
from app.ai.models.knowledge.project_metadata import (
    ProjectMetadata,
)
from app.ai.models.knowledge.risk import Risk
from app.ai.models.knowledge.stakeholder import Stakeholder


class DocumentKnowledgeMapper:
    """
    Converts stored document knowledge dictionaries into
    DocumentKnowledge domain objects.
    """

    def map(
        self,
        data: dict,
    ) -> DocumentKnowledge:
        return DocumentKnowledge(
            project_metadata=self._map_project_metadata(
                data.get("project_metadata"),
            ),
            stakeholders=self._map_stakeholders(
                data.get("stakeholders", []),
            ),
            business_objectives=self._map_business_objectives(
                data.get("business_objectives", []),
            ),
            functional_requirements=self._map_functional_requirements(
                data.get("functional_requirements", []),
            ),
            non_functional_requirements=(
                self._map_non_functional_requirements(
                    data.get(
                        "non_functional_requirements",
                        [],
                    ),
                )
            ),
            assumptions=self._map_assumptions(
                data.get("assumptions", []),
            ),
            constraints=self._map_constraints(
                data.get("constraints", []),
            ),
            risks=self._map_risks(
                data.get("risks", []),
            ),
            decisions=self._map_decisions(
                data.get("decisions", []),
            ),
            out_of_scope=self._map_out_of_scope(
                data.get("out_of_scope", []),
            ),
            open_questions=self._map_open_questions(
                data.get("open_questions", []),
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
        items: list[dict],
    ) -> list[Stakeholder]:
        return [
            Stakeholder(
                name=item.get("name", ""),
                role=item.get("role"),
                organization=item.get("organization"),
            )
            for item in items
        ]

    @staticmethod
    def _map_business_objectives(
        items: list[dict],
    ) -> list[BusinessObjective]:
        return [
            BusinessObjective(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_functional_requirements(
        items: list[dict],
    ) -> list[FunctionalRequirement]:
        return [
            FunctionalRequirement(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_non_functional_requirements(
        items: list[dict],
    ) -> list[NonFunctionalRequirement]:
        return [
            NonFunctionalRequirement(
                category=item.get("category", ""),
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_assumptions(
        items: list[dict],
    ) -> list[Assumption]:
        return [
            Assumption(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_constraints(
        items: list[dict],
    ) -> list[Constraint]:
        return [
            Constraint(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_risks(
        items: list[dict],
    ) -> list[Risk]:
        return [
            Risk(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_decisions(
        items: list[dict],
    ) -> list[Decision]:
        return [
            Decision(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_out_of_scope(
        items: list[dict],
    ) -> list[OutOfScope]:
        return [
            OutOfScope(
                description=item.get("description", ""),
            )
            for item in items
        ]

    @staticmethod
    def _map_open_questions(
        items: list[dict],
    ) -> list[OpenQuestion]:
        return [
            OpenQuestion(
                question=item.get("question", ""),
            )
            for item in items
        ]
