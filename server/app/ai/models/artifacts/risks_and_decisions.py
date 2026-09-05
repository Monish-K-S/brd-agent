from dataclasses import dataclass, field


@dataclass
class RisksAndDecisions:
    risks: list[str] = field(
        default_factory=list
    )

    decisions: list[str] = field(
        default_factory=list
    )
