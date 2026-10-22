"""Structure metric — is the BRD a complete, valid document?

Reuses the same validator the PUT route applies, so "structurally valid"
means exactly what the API means by it. The difference is that the route
raises and this scores: a partial BRD is a *finding*, not an exception.
"""

from app.evals.models import (
    BRD_LIST_FIELDS,
    BRD_TEXT_FIELDS,
)
from app.schemas.brd import (
    ALLOWED_BRD_SECTIONS,
    BRDDataInvalidError,
    BRDDataTooLargeError,
    validate_brd_data,
)


def score_structure(brd: object) -> dict:
    """Score section completeness and schema validity.

    Item counts are computed *before* validation on purpose: when a
    section is missing, the useful information is which of the remaining
    sections are populated, and returning early would throw that away.
    """
    if not isinstance(brd, dict):
        return {
            "valid": False,
            "error": "BRD data is not an object",
            "sections_present": 0,
            "sections_expected": len(ALLOWED_BRD_SECTIONS),
            "empty_sections": [],
            "item_counts": {},
        }

    item_counts = _item_counts(brd)
    empty_sections = _empty_sections(brd, item_counts)

    try:
        validate_brd_data(brd)

        valid = True
        error = None
    except (BRDDataInvalidError, BRDDataTooLargeError) as exc:
        valid = False
        error = str(exc)

    return {
        "valid": valid,
        "error": error,
        "sections_present": len(set(brd) & ALLOWED_BRD_SECTIONS),
        "sections_expected": len(ALLOWED_BRD_SECTIONS),
        "empty_sections": empty_sections,
        "item_counts": item_counts,
    }


def _item_counts(brd: dict) -> dict[str, int]:
    counts: dict[str, int] = {}

    for section, content in brd.items():
        if not isinstance(content, dict):
            continue

        total = 0

        for field in BRD_LIST_FIELDS.get(section, ()):
            value = content.get(field)

            if isinstance(value, list):
                total += len(value)

        if total:
            counts[section] = total

    return counts


def _empty_sections(brd: dict, item_counts: dict[str, int]) -> list[str]:
    """Sections that carry neither list items nor prose."""
    empty = []

    for section, content in brd.items():
        if section not in ALLOWED_BRD_SECTIONS:
            continue

        if not isinstance(content, dict):
            continue

        if item_counts.get(section, 0) > 0:
            continue

        has_text = any(
            isinstance(content.get(field), str)
            and content.get(field, "").strip()
            for field in BRD_TEXT_FIELDS.get(section, ())
        )

        if not has_text:
            empty.append(section)

    return sorted(empty)
