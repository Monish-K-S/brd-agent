from dataclasses import dataclass, field


@dataclass
class BusinessObjectivesSection:
    objectives: list[str] = field(default_factory=list)
