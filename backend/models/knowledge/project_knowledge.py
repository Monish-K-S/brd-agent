from dataclasses import dataclass, field

from models.knowledge.functional_requirement import FunctionalRequirement
from models.knowledge.non_functional_requirement import NonFunctionalRequirement

from models.knowledge.project_metadata import ProjectMetadata
from models.knowledge.stakeholder import Stakeholder


@dataclass
class ProjectKnowledge:
    project_metadata: ProjectMetadata | None = None

    stakeholders: list[Stakeholder] = field(
        default_factory=list
    )

    business_objectives: list[str] = field(
        default_factory=list
    )

    functional_requirements: list[FunctionalRequirement] = field(
        default_factory=list
    )

    non_functional_requirements: list[NonFunctionalRequirement] = field(
        default_factory=list
    )

    assumptions: list[str] = field(
        default_factory=list
    )

    constraints: list[str] = field(
        default_factory=list
    )

    risks: list[str] = field(
        default_factory=list
    )

    decisions: list[str] = field(
        default_factory=list
    )

    out_of_scope: list[str] = field(
        default_factory=list
    )

    open_questions: list[str] = field(
        default_factory=list
    )
