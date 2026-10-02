from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StandardDocumentSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    source_type: str
    title: str | None
    author: str | None
    source_created_at: datetime | None
    participants: list
    metadata: dict
    created_at: datetime
    updated_at: datetime


class StandardDocumentResponse(StandardDocumentSummary):
    content: str
