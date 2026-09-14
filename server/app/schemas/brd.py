from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BRDResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    brd_data: dict
    created_at: datetime
    updated_at: datetime
    user_edited_at: datetime | None


class BRDUpdateRequest(BaseModel):
    brd_data: dict


class BRDStatusResponse(BaseModel):
    has_brd: bool
    has_sources: bool
    has_new_sources: bool
    regeneration_required: bool
    has_user_edits: bool
