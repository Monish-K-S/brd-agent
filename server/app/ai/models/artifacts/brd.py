from dataclasses import dataclass

from app.ai.models.artifacts.assumptions_and_constraints import (
    AssumptionsAndConstraints,
)
from app.ai.models.artifacts.business_objectives_section import (
    BusinessObjectivesSection,
)
from app.ai.models.artifacts.business_requirements import BusinessRequirements
from app.ai.models.artifacts.executive_summary import ExecutiveSummary
from app.ai.models.artifacts.functional_requirements_section import (
    FunctionalRequirementsSection,
)
from app.ai.models.artifacts.non_functional_requirements_section import (
    NonFunctionalRequirementsSection,
)
from app.ai.models.artifacts.open_questions_section import OpenQuestionsSection
from app.ai.models.artifacts.project_overview import ProjectOverview
from app.ai.models.artifacts.risks_and_decisions import RisksAndDecisions
from app.ai.models.artifacts.scope import Scope
from app.ai.models.artifacts.stakeholders_section import StakeholdersSection


@dataclass
class BRD:
    executive_summary: ExecutiveSummary

    project_overview: ProjectOverview

    business_objectives: BusinessObjectivesSection

    scope: Scope

    stakeholders: StakeholdersSection

    business_requirements: BusinessRequirements

    functional_requirements: FunctionalRequirementsSection

    non_functional_requirements: NonFunctionalRequirementsSection

    assumptions_and_constraints: AssumptionsAndConstraints

    risks_and_decisions: RisksAndDecisions

    open_questions: OpenQuestionsSection
