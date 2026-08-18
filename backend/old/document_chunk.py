from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class DocumentChunk:
    """
    Represent a searchable chunk extracted from a StandardDocument
    """

    id: UUID = field(default_factory=uuid4)

    document_id: UUID | None = None

    chunk_index: int = 0

    source_type: str = ""

    content: str = ""

    metadata: dict = field(default_factory=dict)
