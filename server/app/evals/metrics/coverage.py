"""Coverage metric — did the BRD capture what the documents said?

This is the only metric in the harness that needs a reference answer, and
therefore the only one that cannot run on a real generation. For each
scenario, ``expected.json`` lists atomic facts, each with one or more
groups of accepted phrasings:

    {"id": "f1", "text": "Users sign in with Google SSO",
     "groups": [["google"], ["sso", "single sign-on", "single sign on"]]}

A fact counts as captured when **every** group has at least one
alternative present. Requiring all groups is what keeps a fact from
passing on a single common word; allowing alternatives within a group is
what keeps a correct paraphrase from being scored as a miss.

Matching is substring on normalized text, which is deliberately literal.
It cannot recognise a fact stated in words nobody anticipated, so the
report always shows the missed facts — "recall 0.79" alone would hide
whether the pipeline failed or the ground truth was too narrow.
"""

import re

from app.evals.models import iter_brd_text_items

_DASHES = re.compile(r"[-\u2013\u2014]+")


def score_coverage(brd: object, expected: object) -> dict:
    """Score fact recall for one scenario."""
    if not isinstance(expected, dict):
        return _unavailable("no expected facts available")

    facts = expected.get("facts")

    if not isinstance(facts, list) or not facts:
        return _unavailable("expected.json lists no facts")

    corpus = _normalize(_flatten_brd(brd))

    scored = 0
    missed = []
    invalid = []

    for fact in facts:
        if not isinstance(fact, dict):
            invalid.append({"reason": "fact is not an object"})

            continue

        groups = [
            group
            for group in fact.get("groups") or []
            if isinstance(group, list) and group
        ]

        # A fact with no usable group would match everything, which would
        # silently inflate recall. It is an authoring error, so it is
        # reported instead of counted as either outcome.
        if not groups:
            invalid.append(
                {
                    "id": fact.get("id"),
                    "reason": "no accepted phrasings",
                }
            )

            continue

        scored += 1

        missing_groups = [
            group
            for group in groups
            if not any(_alternative_present(alt, corpus) for alt in group)
        ]

        if missing_groups:
            missed.append(
                {
                    "id": fact.get("id"),
                    "text": fact.get("text"),
                    "missing_groups": missing_groups,
                }
            )

    matched = scored - len(missed)

    return {
        "available": True,
        "reason": None,
        "facts_total": scored,
        "facts_matched": matched,
        "recall": round(matched / scored, 3) if scored else None,
        "missed": missed,
        "invalid": invalid,
    }


def _flatten_brd(brd: object) -> str:
    return " ".join(text for _, text in iter_brd_text_items(brd))


def _normalize(text: object) -> str:
    """Lowercase, flatten dashes, collapse whitespace.

    Dashes are flattened to spaces so ``single sign-on`` and
    ``single sign on`` are the same phrase — the model is free to write
    either, and treating them as different facts would be scoring
    punctuation, not content.
    """
    if not isinstance(text, str):
        return ""

    return " ".join(_DASHES.sub(" ", text).split()).lower()


def _alternative_present(alternative: object, corpus: str) -> bool:
    normalized = _normalize(alternative)

    return bool(normalized) and normalized in corpus


def _unavailable(reason: str) -> dict:
    return {
        "available": False,
        "reason": reason,
        "facts_total": 0,
        "facts_matched": 0,
        "recall": None,
        "missed": [],
        "invalid": [],
    }
