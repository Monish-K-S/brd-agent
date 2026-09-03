from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentExtractionResponse(BaseModel):
    id: UUID

    workspace_id: UUID

    document_knowledge: dict

    created_at: datetime

    updated_at: datetime
