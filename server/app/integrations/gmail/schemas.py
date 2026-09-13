from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GmailMessageSummary(BaseModel):
    id: str
    thread_id: str | None = None
    subject: str | None = None
    sender: str | None = None
    date: datetime | None = None
    snippet: str | None = None


class GmailMessageListResponse(BaseModel):
    messages: list[GmailMessageSummary]


class GmailImportRequest(BaseModel):
    message_ids: list[str] = Field(
        min_length=1,
        max_length=20,
    )


class GmailImportedDocument(BaseModel):
    id: UUID
    gmail_message_id: str
    title: str | None = None


class GmailImportResponse(BaseModel):
    imported: list[GmailImportedDocument]
    skipped_message_ids: list[str]
