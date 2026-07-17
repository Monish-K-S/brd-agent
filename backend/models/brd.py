from dataclasses import dataclass, field
from uuid import UUID, uuid4

from models.requirement import Requirement

@dataclass
class BRD:
    """
    Represents a Business Requirement Document
    """

    project_name: str

    executive_summary: str

    business_objective: list[str]

    functional_requirements: list[Requirement]

    non_functional_requirements: list[Requirement]

    id: UUID = field(default_factory=uuid4)
