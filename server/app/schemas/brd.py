import json
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


ALLOWED_BRD_SECTIONS = frozenset(
    {
        "executive_summary",
        "project_overview",
        "business_objectives",
        "scope",
        "stakeholders",
        "business_requirements",
        "functional_requirements",
        "non_functional_requirements",
        "assumptions_and_constraints",
        "risks_and_decisions",
        "open_questions",
    }
)

MAX_BRD_DATA_BYTES = 1024 * 1024
MAX_BRD_DATA_DEPTH = 6
MAX_BRD_STRING_CHARS = 50_000


class BRDDataTooLargeError(ValueError):
    pass


class BRDDataInvalidError(ValueError):
    pass


def _check_brd_value(value: object, depth: int) -> None:
    if depth > MAX_BRD_DATA_DEPTH:
        raise BRDDataInvalidError(
            "BRD data is nested too deeply "
            f"(max depth {MAX_BRD_DATA_DEPTH})"
        )

    if isinstance(value, str):
        if len(value) > MAX_BRD_STRING_CHARS:
            raise BRDDataTooLargeError(
                "BRD text value too large "
                f"(max {MAX_BRD_STRING_CHARS} characters)"
            )

        return

    if isinstance(value, dict):
        for item in value.values():
            _check_brd_value(item, depth + 1)

        return

    if isinstance(value, list):
        for item in value:
            _check_brd_value(item, depth + 1)

        return


def validate_brd_data(brd_data: dict) -> None:
    unknown = set(brd_data) - ALLOWED_BRD_SECTIONS

    if unknown:
        raise BRDDataInvalidError(
            "Unknown BRD sections: "
            + ", ".join(sorted(str(key) for key in unknown))
        )

    for section, content in brd_data.items():
        if not isinstance(content, dict):
            raise BRDDataInvalidError(
                f"BRD section {section!r} must be an object"
            )

    _check_brd_value(brd_data, 0)

    if len(json.dumps(brd_data)) > MAX_BRD_DATA_BYTES:
        raise BRDDataTooLargeError(
            "BRD data too large "
            f"(max {MAX_BRD_DATA_BYTES // 1024}KB)"
        )


class BRDStatusResponse(BaseModel):
    has_brd: bool
    has_sources: bool
    has_new_sources: bool
    regeneration_required: bool
    has_user_edits: bool
