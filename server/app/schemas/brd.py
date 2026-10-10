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


class BRDMalformedError(ValueError):
    """Stored BRD data that passed validation earlier (or predates it)
    but cannot be mapped for export. Surfaces as a 422 with a
    regenerate hint instead of a 500 KeyError."""


# Fields BRDMapper hard-reads (data["..."] / entry["name"]) — everything
# else in the mapper already uses .get() with safe defaults, so only
# these need enforcing. Mirrors app/ai/mappers/brd_mapper.py.
_REQUIRED_BRD_FIELDS = {
    "executive_summary": {"content": str},
    "project_overview": {"project_name": str, "description": str},
}

# Plural fields the mapper wraps in list(...) — a non-list here would
# silently shred (list("abc") -> ["a", "b", "c"]) or crash downstream.
_REQUIRED_BRD_LISTS = {
    "business_objectives": ("objectives",),
    "scope": ("in_scope", "out_of_scope"),
    "stakeholders": ("stakeholders",),
    "business_requirements": ("requirements",),
    "functional_requirements": ("requirements",),
    "non_functional_requirements": ("requirements",),
    "assumptions_and_constraints": ("assumptions", "constraints"),
    "risks_and_decisions": ("risks", "decisions"),
    "open_questions": ("questions",),
}


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

    # The exporter hard-reads every section (BRDMapper.map does
    # data["executive_summary"] etc.), so a partial body that passes the
    # checks above would persist and then 500 both downloads (H-2).
    missing = ALLOWED_BRD_SECTIONS - set(brd_data)

    if missing:
        raise BRDDataInvalidError(
            "Missing BRD sections: " + ", ".join(sorted(missing))
        )

    for section, fields in _REQUIRED_BRD_FIELDS.items():
        content = brd_data[section]

        for field, kind in fields.items():
            if not isinstance(content.get(field), kind):
                raise BRDDataInvalidError(
                    f"BRD section {section!r} must include "
                    f"{field!r} as a string"
                )

    for section, lists in _REQUIRED_BRD_LISTS.items():
        content = brd_data[section]

        for field in lists:
            if field in content and not isinstance(content[field], list):
                raise BRDDataInvalidError(
                    f"BRD section {section!r} field {field!r} "
                    "must be a list"
                )

    for entry in brd_data["stakeholders"].get("stakeholders", []):
        if not isinstance(entry, dict) or not isinstance(
            entry.get("name"), str
        ):
            raise BRDDataInvalidError(
                "Each stakeholder entry must include 'name' as a string"
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
    active_job: "GenerationJobResponse | None" = None
    last_job: "GenerationJobResponse | None" = None


class GenerationJobResponse(BaseModel):
    job_id: UUID
    status: str
    phase: str | None = None
    error: str | None = None
