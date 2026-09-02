from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StandardDocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    source_type: str
    title: str | None
    author: str | None
    source_created_at: datetime | None
    participants: list
    content: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
