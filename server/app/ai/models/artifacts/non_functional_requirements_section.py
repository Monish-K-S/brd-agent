from dataclasses import dataclass, field


@dataclass
class NonFunctionalRequirementsSection:
    requirements: list[str] = field(
        default_factory=list
    )
