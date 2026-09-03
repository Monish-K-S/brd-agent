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
from app.ai.models.knowledge.project_metadata import ProjectMetadata
from app.ai.models.knowledge.risk import Risk
from app.ai.models.knowledge.stakeholder import Stakeholder


class SarvamKnowledgeMapper:
    """
    Maps the result section of a Sarvam Document AI response
    into a DocumentKnowledge object.
    """

    def map(
        self,
        sarvam_response: dict,
    ) -> DocumentKnowledge:
        result = sarvam_response.get(
            "result",
            {},
        )

        return DocumentKnowledge(
            project_metadata=self._map_project_metadata(
                result.get("project_metadata")
            ),
            stakeholders=self._map_stakeholders(
                result.get("stakeholders", [])
            ),
            business_objectives=self._map_business_objectives(
                result.get("business_objectives", [])
            ),
            functional_requirements=self._map_functional_requirements(
                result.get("functional_requirements", [])
            ),
            non_functional_requirements=(
                self._map_non_functional_requirements(
                    result.get(
                        "non_functional_requirements",
                        [],
                    )
                )
            ),
            assumptions=self._map_assumptions(
                result.get("assumptions", [])
            ),
            constraints=self._map_constraints(
                result.get("constraints", [])
            ),
            risks=self._map_risks(
                result.get("risks", [])
            ),
            decisions=self._map_decisions(
                result.get("decisions", [])
            ),
            out_of_scope=self._map_out_of_scope(
                result.get("out_of_scope", [])
            ),
            open_questions=self._map_open_questions(
                result.get("open_questions", [])
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
                organization=stakeholder.get(
                    "organization"
                ),
            )
            for stakeholder in stakeholders
        ]

    @staticmethod
    def _map_business_objectives(
        objectives: list[str],
    ) -> list[BusinessObjective]:
        return [
            BusinessObjective(
                description=objective,
            )
            for objective in objectives
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

    @staticmethod
    def _map_assumptions(
        assumptions: list[str],
    ) -> list[Assumption]:
        return [
            Assumption(
                description=assumption,
            )
            for assumption in assumptions
        ]

    @staticmethod
    def _map_constraints(
        constraints: list[str],
    ) -> list[Constraint]:
        return [
            Constraint(
                description=constraint,
            )
            for constraint in constraints
        ]

    @staticmethod
    def _map_risks(
        risks: list[str],
    ) -> list[Risk]:
        return [
            Risk(
                description=risk,
            )
            for risk in risks
        ]

    @staticmethod
    def _map_decisions(
        decisions: list[str],
    ) -> list[Decision]:
        return [
            Decision(
                description=decision,
            )
            for decision in decisions
        ]

    @staticmethod
    def _map_out_of_scope(
        items: list[str],
    ) -> list[OutOfScope]:
        return [
            OutOfScope(
                description=item,
            )
            for item in items
        ]

    @staticmethod
    def _map_open_questions(
        questions: list[str],
    ) -> list[OpenQuestion]:
        return [
            OpenQuestion(
                question=question,
            )
            for question in questions
        ]
