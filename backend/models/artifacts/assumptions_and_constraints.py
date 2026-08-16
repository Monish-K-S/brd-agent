from dataclasses import dataclass, field


@dataclass
class AssumptionsAndConstraints:
    assumptions: list[str] = field(
        default_factory=list
    )

    constraints: list[str] = field(
        default_factory=list
    )
