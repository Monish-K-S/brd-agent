from dataclasses import dataclass

from models.requirement import Requirement

@dataclass
class RequirementExtractionResult:
    """
    Contains all requirements extracted from a project.
    """

    functional_requirements: list[Requirement]
    non_functional_requirements: list[Requirement]
