from uuid import UUID

from pydantic import BaseModel, Field


class BRDQARequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=2000,
    )


class BRDQASource(BaseModel):
    id: UUID
    title: str | None
    source_type: str


class BRDQAResponse(BaseModel):
    answer: str
    sources: list[BRDQASource] = Field(
        default_factory=list,
    )
