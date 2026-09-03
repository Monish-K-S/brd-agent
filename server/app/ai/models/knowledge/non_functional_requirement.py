from dataclasses import dataclass


@dataclass
class NonFunctionalRequirement:
    category: str
    description: str
