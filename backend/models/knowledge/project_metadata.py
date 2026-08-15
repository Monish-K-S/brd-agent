from dataclasses import dataclass

@dataclass
class ProjectMetadata:
    project_name: str | None = None
    description: str | None = None
