from dataclasses import dataclass, field


@dataclass
class FunctionalRequirementsSection:
    requirements: list[str] = field(
        default_factory=list
    )
