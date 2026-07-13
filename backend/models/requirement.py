from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class Requirement:
    """
    Represent a single business requirement extracted by the LLM
    """

    requirement_type: str
    description: str
    source_chunk_ids: list[UUID]

    id: UUID = field(default_factory=uuid4)
