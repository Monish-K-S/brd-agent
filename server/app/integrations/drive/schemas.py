import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


DRIVE_FILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


class DriveFileImportRequest(BaseModel):
    drive_file_ids: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator("drive_file_ids")
    @classmethod
    def validate_drive_file_ids(cls, value: list[str]) -> list[str]:
        for drive_file_id in value:
            if not DRIVE_FILE_ID_PATTERN.match(drive_file_id):
                raise ValueError(
                    f"Invalid Drive file ID: {drive_file_id!r}"
                )

        return value


class DriveImportedDocument(BaseModel):
    id: UUID
    drive_file_id: str
    title: str | None = None


class DriveFileImportResponse(BaseModel):
    imported: list[DriveImportedDocument]
    skipped_file_ids: list[str]
