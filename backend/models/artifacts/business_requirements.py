from dataclasses import dataclass, field


@dataclass
class BusinessRequirements:
    requirements: list[str] = field(
        default_factory=list
    )
