from dataclasses import dataclass, field


@dataclass
class Evidence:
    document_id: str
    excerpt: str


@dataclass
class ProjectInformation:
    name: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class FunctionalRequirement:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class NonFunctionalRequirement:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class BusinessObjective:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Stakeholder:
    name: str
    role: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Constraint:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Assumption:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Decision:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class Risk:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class OpenQuestion:
    description: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class DocumentAnalysis:
    project_information: ProjectInformation | None = None

    stakeholders: list[Stakeholder] = field(default_factory=list)

    business_objectives: list[BusinessObjective] = field(default_factory=list)

    functional_requirements: list[FunctionalRequirement] = field(default_factory=list)

    non_functional_requirements: list[NonFunctionalRequirement] = field(default_factory=list)

    constraints: list[Constraint] = field(default_factory=list)

    assumptions: list[Assumption] = field(default_factory=list)

    decisions: list[Decision] = field(default_factory=list)

    risks: list[Risk] = field(default_factory=list)

    open_questions: list[OpenQuestion] = field(default_factory=list)
