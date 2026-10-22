"""Groundedness metric — is every BRD line traceable to the sources?

The prompt forbids inventing requirements, stakeholders and risks. This
checks that by asking, for each BRD item, how much of its vocabulary also
appears in the project knowledge it was generated from.

This is a **lexical** check, and the result says so (``method``), because
it cannot distinguish "restated in different words" from "invented". It
flags *suspect* items for a human to look at; it does not prove a
hallucination. Claiming otherwise would be the easiest thing to disprove
in a review.
"""

from dataclasses import asdict, is_dataclass

from app.evals.models import iter_brd_text_items
from app.evals.text import content_words

SUPPORT_THRESHOLD = 0.5

METHOD = "lexical-overlap"


def score_groundedness(
    brd: object,
    knowledge: object,
) -> dict:
    """Flag BRD items whose vocabulary is largely absent from the sources."""
    if knowledge is None:
        return {
            "available": False,
            "reason": "no project knowledge available",
            "method": METHOD,
            "items_scored": 0,
            "supported": 0,
            "items_skipped": 0,
            "unsupported": [],
            "unsupported_rate": None,
        }

    corpus_words = content_words(_knowledge_text(knowledge))

    items_scored = 0
    items_skipped = 0
    unsupported = []

    for section, text in iter_brd_text_items(brd):
        item_words = content_words(text)

        # An item made entirely of stop words or short tokens carries no
        # evidence either way. Counting it as supported would inflate the
        # score; counting it as unsupported would invent a finding.
        if not item_words:
            items_skipped += 1

            continue

        items_scored += 1

        score = len(item_words & corpus_words) / len(item_words)

        if score < SUPPORT_THRESHOLD:
            unsupported.append(
                {
                    "section": section,
                    "text": text,
                    "score": round(score, 3),
                }
            )

    supported = items_scored - len(unsupported)

    return {
        "available": True,
        "reason": None,
        "method": METHOD,
        "items_scored": items_scored,
        "supported": supported,
        "items_skipped": items_skipped,
        "unsupported": unsupported,
        "unsupported_rate": (
            round(len(unsupported) / items_scored, 3)
            if items_scored
            else None
        ),
    }


def _knowledge_text(knowledge: object) -> str:
    """Flatten every string in the knowledge object into one corpus."""
    payload = (
        asdict(knowledge)
        if is_dataclass(knowledge) and not isinstance(knowledge, type)
        else knowledge
    )

    parts: list[str] = []

    _collect_strings(payload, parts)

    return " ".join(parts)


def _collect_strings(value: object, parts: list[str]) -> None:
    if isinstance(value, str):
        parts.append(value)

        return

    if isinstance(value, dict):
        for item in value.values():
            _collect_strings(item, parts)

        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_strings(item, parts)
