from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BRDResponse(BaseModel):
    id: UUID

    workspace_id: UUID

    brd_data: dict

    created_at: datetime

    updated_at: datetime
