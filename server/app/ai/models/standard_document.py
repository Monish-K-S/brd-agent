from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class StandardDocument:
    """
    Internal representation of a document used by the AI pipeline.

    All external sources are converted into this common format
    before normalization and further AI processing.
    """

    id: UUID = field(default_factory=uuid4)

    source_type: str = ""

    title: str | None = None

    author: str | None = None

    source_created_at: datetime | None = None

    participants: list[str] = field(default_factory=list)

    content: str = ""

    metadata: dict = field(default_factory=dict)
