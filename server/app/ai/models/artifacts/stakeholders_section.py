from dataclasses import dataclass, field


@dataclass
class StakeholderEntry:
    name: str
    role: str | None = None
    organization: str | None = None


@dataclass
class StakeholdersSection:
    stakeholders: list[StakeholderEntry] = field(
        default_factory=list
    )
