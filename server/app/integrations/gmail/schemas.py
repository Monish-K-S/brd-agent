import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GmailMessageSummary(BaseModel):
    id: str
    thread_id: str | None = None
    subject: str | None = None
    sender: str | None = None
    date: datetime | None = None
    snippet: str | None = None


class GmailMessageListResponse(BaseModel):
    messages: list[GmailMessageSummary]


GMAIL_MESSAGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class GmailImportRequest(BaseModel):
    message_ids: list[str] = Field(
        min_length=1,
        max_length=20,
    )

    @field_validator("message_ids")
    @classmethod
    def validate_message_ids(cls, value: list[str]) -> list[str]:
        for message_id in value:
            if not GMAIL_MESSAGE_ID_PATTERN.match(message_id):
                raise ValueError(
                    f"Invalid Gmail message ID: {message_id!r}"
                )

        return value


class GmailImportedDocument(BaseModel):
    id: UUID
    gmail_message_id: str
    title: str | None = None


class GmailImportResponse(BaseModel):
    imported: list[GmailImportedDocument]
    skipped_message_ids: list[str]
