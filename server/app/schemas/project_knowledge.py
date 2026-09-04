from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectKnowledgeResponse(BaseModel):
    id: UUID

    workspace_id: UUID

    knowledge_data: dict

    created_at: datetime

    updated_at: datetime
