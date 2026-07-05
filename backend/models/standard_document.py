from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class StandardDocument:
    """
    Internal representation of any document ingested by the system.
    Regardless of the source (TXT, Email, Transcript), every parser
    should return a StandardDocument.
    """

    id: UUID = field(default_factory=uuid4)

    source_type: str = ""

    title: str | None = None

    author: str | None = None

    created_at: datetime | None = None

    participants: list[str] = field(default_factory=list)

    content: str = ""

    metadata: dict = field(default_factory=dict)
