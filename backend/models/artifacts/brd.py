from dataclasses import dataclass

from models.artifacts.assumptions_and_constraints import (
    AssumptionsAndConstraints,
)
from models.artifacts.business_objectives_section import (
    BusinessObjectivesSection,
)
from models.artifacts.business_requirements import BusinessRequirements
from models.artifacts.executive_summary import ExecutiveSummary
from models.artifacts.functional_requirements_section import (
    FunctionalRequirementsSection,
)
from models.artifacts.non_functional_requirements_section import (
    NonFunctionalRequirementsSection,
)
from models.artifacts.open_questions_section import OpenQuestionsSection
from models.artifacts.project_overview import ProjectOverview
from models.artifacts.risks_and_decisions import RisksAndDecisions
from models.artifacts.scope import Scope
from models.artifacts.stakeholders_section import StakeholdersSection


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
