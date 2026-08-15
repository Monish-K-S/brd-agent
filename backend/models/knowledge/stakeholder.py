from dataclasses import dataclass


@dataclass
class Stakeholder:
    name: str
    role: str | None = None
    organization: str | None = None
