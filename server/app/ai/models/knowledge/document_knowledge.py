from dataclasses import dataclass, field

from app.ai.models.knowledge.assumption import Assumption
from app.ai.models.knowledge.business_objective import BusinessObjective
from app.ai.models.knowledge.constraint import Constraint
from app.ai.models.knowledge.decision import Decision
from app.ai.models.knowledge.functional_requirement import FunctionalRequirement
from app.ai.models.knowledge.non_functional_requirement import NonFunctionalRequirement
from app.ai.models.knowledge.open_question import OpenQuestion
from app.ai.models.knowledge.out_of_scope import OutOfScope
from app.ai.models.knowledge.project_metadata import ProjectMetadata
from app.ai.models.knowledge.risk import Risk
from app.ai.models.knowledge.stakeholder import Stakeholder


@dataclass
class DocumentKnowledge:
    project_metadata: ProjectMetadata | None = None

    stakeholders: list[Stakeholder] = field(default_factory=list)

    business_objectives: list[BusinessObjective] = field(default_factory=list)

    functional_requirements: list[FunctionalRequirement] = field(default_factory=list)

    non_functional_requirements: list[NonFunctionalRequirement] = field(
        default_factory=list
    )

    assumptions: list[Assumption] = field(default_factory=list)

    constraints: list[Constraint] = field(default_factory=list)

    risks: list[Risk] = field(default_factory=list)

    decisions: list[Decision] = field(default_factory=list)

    out_of_scope: list[OutOfScope] = field(default_factory=list)

    open_questions: list[OpenQuestion] = field(default_factory=list)
