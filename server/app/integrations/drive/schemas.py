import re
from uuid import UUID

from pydantic import BaseModel, field_validator


DRIVE_FILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


class DriveFileImportRequest(BaseModel):
    drive_file_id: str

    @field_validator("drive_file_id")
    @classmethod
    def validate_drive_file_id(cls, value: str) -> str:
        if not DRIVE_FILE_ID_PATTERN.match(value):
            raise ValueError(
                f"Invalid Drive file ID: {value!r}"
            )

        return value


class DriveFileImportResponse(BaseModel):
    id: UUID | None = None
    drive_file_id: str
    title: str | None = None
    skipped: bool = False
