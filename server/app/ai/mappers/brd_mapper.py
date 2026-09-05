from app.ai.models.artifacts.assumptions_and_constraints import (
    AssumptionsAndConstraints,
)
from app.ai.models.artifacts.brd import BRD
from app.ai.models.artifacts.business_objectives_section import (
    BusinessObjectivesSection,
)
from app.ai.models.artifacts.business_requirements import (
    BusinessRequirements,
)
from app.ai.models.artifacts.executive_summary import ExecutiveSummary
from app.ai.models.artifacts.functional_requirements_section import (
    FunctionalRequirementsSection,
)
from app.ai.models.artifacts.non_functional_requirements_section import (
    NonFunctionalRequirementsSection,
)
from app.ai.models.artifacts.open_questions_section import (
    OpenQuestionsSection,
)
from app.ai.models.artifacts.project_overview import ProjectOverview
from app.ai.models.artifacts.risks_and_decisions import RisksAndDecisions
from app.ai.models.artifacts.scope import Scope
from app.ai.models.artifacts.stakeholders_section import (
    StakeholderEntry,
    StakeholdersSection,
)


class BRDMapper:
    """
    Maps structured Gemini BRD JSON into the application's
    BRD domain model.
    """

    def map(self, data: dict) -> BRD:
        return BRD(
            executive_summary=self._map_executive_summary(data["executive_summary"]),
            project_overview=self._map_project_overview(data["project_overview"]),
            business_objectives=self._map_business_objectives(
                data["business_objectives"]
            ),
            scope=self._map_scope(data["scope"]),
            stakeholders=self._map_stakeholders(data["stakeholders"]),
            business_requirements=self._map_business_requirements(
                data["business_requirements"]
            ),
            functional_requirements=self._map_functional_requirements(
                data["functional_requirements"]
            ),
            non_functional_requirements=(
                self._map_non_functional_requirements(
                    data["non_functional_requirements"]
                )
            ),
            assumptions_and_constraints=(
                self._map_assumptions_and_constraints(
                    data["assumptions_and_constraints"]
                )
            ),
            risks_and_decisions=self._map_risks_and_decisions(
                data["risks_and_decisions"]
            ),
            open_questions=self._map_open_questions(data["open_questions"]),
        )

    @staticmethod
    def _map_executive_summary(
        data: dict,
    ) -> ExecutiveSummary:
        return ExecutiveSummary(content=data["content"])

    @staticmethod
    def _map_project_overview(
        data: dict,
    ) -> ProjectOverview:
        return ProjectOverview(
            project_name=data["project_name"],
            description=data["description"],
        )

    @staticmethod
    def _map_business_objectives(
        data: dict,
    ) -> BusinessObjectivesSection:
        return BusinessObjectivesSection(objectives=list(data.get("objectives", [])))

    @staticmethod
    def _map_scope(
        data: dict,
    ) -> Scope:
        return Scope(
            in_scope=list(data.get("in_scope", [])),
            out_of_scope=list(data.get("out_of_scope", [])),
        )

    @staticmethod
    def _map_stakeholders(
        data: dict,
    ) -> StakeholdersSection:
        stakeholders = [
            StakeholderEntry(
                name=stakeholder["name"],
                role=stakeholder.get("role"),
                organization=stakeholder.get("organization"),
            )
            for stakeholder in data.get(
                "stakeholders",
                [],
            )
        ]

        return StakeholdersSection(stakeholders=stakeholders)

    @staticmethod
    def _map_business_requirements(
        data: dict,
    ) -> BusinessRequirements:
        return BusinessRequirements(requirements=list(data.get("requirements", [])))

    @staticmethod
    def _map_functional_requirements(
        data: dict,
    ) -> FunctionalRequirementsSection:
        return FunctionalRequirementsSection(
            requirements=list(data.get("requirements", []))
        )

    @staticmethod
    def _map_non_functional_requirements(
        data: dict,
    ) -> NonFunctionalRequirementsSection:
        return NonFunctionalRequirementsSection(
            requirements=list(data.get("requirements", []))
        )

    @staticmethod
    def _map_assumptions_and_constraints(
        data: dict,
    ) -> AssumptionsAndConstraints:
        return AssumptionsAndConstraints(
            assumptions=list(data.get("assumptions", [])),
            constraints=list(data.get("constraints", [])),
        )

    @staticmethod
    def _map_risks_and_decisions(
        data: dict,
    ) -> RisksAndDecisions:
        return RisksAndDecisions(
            risks=list(data.get("risks", [])),
            decisions=list(data.get("decisions", [])),
        )

    @staticmethod
    def _map_open_questions(
        data: dict,
    ) -> OpenQuestionsSection:
        return OpenQuestionsSection(questions=list(data.get("questions", [])))
