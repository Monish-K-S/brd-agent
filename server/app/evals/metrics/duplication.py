"""Duplication metric — does the BRD repeat itself?

The consolidator drops byte-identical knowledge items before generation
(Batch G), so a duplicate in the *output* means the model repeated itself
or merged nothing while claiming to. Either way it is a quality defect
the user sees.

Normalization is limited to case, whitespace and edge punctuation —
never digits — for the same reason the consolidator's key never touches
digits: "3.5 seconds" and "35 seconds" are different requirements and
must not be collapsed into one.
"""

from app.evals.models import iter_brd_text_items

# Below this, a repeat is more likely to be a label ("Yes", "N/A") than
# duplicated content. Those are skipped outright rather than reported as
# findings nobody would act on.
MIN_DUPLICATE_CHARS = 12

_EDGE_PUNCTUATION = " \t\r\n.,;:!?\"'()[]{}<>-–—*"


def score_duplication(brd: object) -> dict:
    """Count items that repeat elsewhere in the document."""
    groups: dict[str, dict] = {}
    total_items = 0
    skipped_short = 0

    for section, text in iter_brd_text_items(brd):
        key = _duplicate_key(text)

        if len(key) < MIN_DUPLICATE_CHARS:
            skipped_short += 1

            continue

        total_items += 1

        entry = groups.setdefault(
            key,
            {"text": text, "count": 0, "sections": []},
        )

        entry["count"] += 1

        if section not in entry["sections"]:
            entry["sections"].append(section)

    duplicates = [
        {
            "text": entry["text"],
            "count": entry["count"],
            "sections": entry["sections"],
        }
        for entry in groups.values()
        if entry["count"] > 1
    ]

    duplicate_items = sum(item["count"] - 1 for item in duplicates)

    return {
        "total_items": total_items,
        "duplicate_items": duplicate_items,
        "duplicate_groups": len(duplicates),
        "rate": (
            round(duplicate_items / total_items, 3)
            if total_items
            else 0.0
        ),
        "skipped_short": skipped_short,
        "duplicates": duplicates,
    }


def _duplicate_key(text: str) -> str:
    return " ".join(text.split()).lower().strip(_EDGE_PUNCTUATION)
