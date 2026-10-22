"""Shared vocabulary for the evaluation metrics.

The BRD is a plain dict with eleven sections. Two shapes appear in it:
sections whose substance is a list of items, and sections whose substance
is one or two prose fields. Every metric needs to walk both shapes, so the
walk lives here once instead of being re-derived per metric.
"""

from collections.abc import Iterator

# section -> the list fields the BRD schema defines for it.
# Mirrors ``app.schemas.brd._REQUIRED_BRD_LISTS``; a test asserts the two
# agree, so a new section cannot be added to one and silently missed by
# the other.
BRD_LIST_FIELDS: dict[str, tuple[str, ...]] = {
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

# Sections whose substance is prose rather than a list.
BRD_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "executive_summary": ("content",),
    "project_overview": ("project_name", "description"),
}


def item_text(item: object) -> str:
    """Flatten one BRD list item to text.

    Most items are strings, but ``stakeholders`` holds objects with a
    ``name``/``role`` shape. Flattening rather than special-casing keeps
    every metric able to score any section.
    """
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return " ".join(
            value
            for value in item.values()
            if isinstance(value, str) and value.strip()
        )

    return str(item)


def iter_brd_text_items(brd: object) -> Iterator[tuple[str, str]]:
    """Yield ``(section, text)`` for every scorable item in a BRD.

    Blank entries are skipped: an empty list item is a structural defect
    (reported by the structure metric), not text to be scored for
    duplication or groundedness.
    """
    if not isinstance(brd, dict):
        return

    for section, content in brd.items():
        if not isinstance(content, dict):
            continue

        for field in BRD_LIST_FIELDS.get(section, ()):
            value = content.get(field)

            if not isinstance(value, list):
                continue

            for item in value:
                text = item_text(item).strip()

                if text:
                    yield section, text

        for field in BRD_TEXT_FIELDS.get(section, ()):
            value = content.get(field)

            if isinstance(value, str) and value.strip():
                yield section, value.strip()
