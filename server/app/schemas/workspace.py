from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

MAX_WORKSPACE_NAME_CHARS = 200


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_and_validate_name(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError("Workspace name must not be blank")

        if len(stripped) > MAX_WORKSPACE_NAME_CHARS:
            raise ValueError(
                "Workspace name too long "
                f"(max {MAX_WORKSPACE_NAME_CHARS} characters)"
            )

        return stripped


class WorkspaceResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
