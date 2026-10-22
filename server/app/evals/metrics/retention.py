"""Retention metric — did the BRD keep every requirement it was given?

This is the highest-value automatic check. The generation prompt tells
the model that "every functional requirement from ProjectKnowledge must
remain represented unless it is genuinely duplicated without loss of
meaning", so the failure it guards against is silent: fifteen extracted
requirements go in, nine come out, and nothing in the pipeline notices.

No ground truth is needed — the input knowledge *is* the reference — which
is why this can run on every real generation for free.

Matching is token overlap rather than string equality because the model
is explicitly allowed to reword. The threshold is a floor, not a target:
a requirement that scores below it is reported with its best match and
score so a human can judge whether it was genuinely dropped.
"""

from app.evals.text import content_words

RETENTION_THRESHOLD = 0.6


def score_retention(
    knowledge: object,
    brd: object,
) -> dict:
    """Compare extracted requirements against the generated BRD."""
    if knowledge is None:
        return {
            "available": False,
            "reason": "no project knowledge available",
            "functional": _empty_group(),
            "non_functional": _empty_group(),
            "overall_retention": None,
        }

    functional = _score_group(
        source_texts=[
            getattr(item, "description", "")
            for item in getattr(knowledge, "functional_requirements", [])
        ],
        target_texts=_section_items(brd, "functional_requirements"),
    )

    non_functional = _score_group(
        source_texts=[
            getattr(item, "description", "")
            for item in getattr(knowledge, "non_functional_requirements", [])
        ],
        target_texts=_section_items(brd, "non_functional_requirements"),
    )

    return {
        "available": True,
        "reason": None,
        "functional": functional,
        "non_functional": non_functional,
        "overall_retention": _combined_retention(
            functional,
            non_functional,
        ),
    }


def _score_group(
    source_texts: list[str],
    target_texts: list[str],
) -> dict:
    """Score one requirement group.

    ``retention`` is ``None`` when there was nothing to check. That is not
    the same as 1.0: "no requirements were extracted" is an input problem,
    and reporting it as perfect would hide it.
    """
    sources = [
        text
        for text in source_texts
        if isinstance(text, str) and text.strip()
    ]

    if not sources:
        return _empty_group()

    targets = [
        (text, content_words(text))
        for text in target_texts
        if isinstance(text, str) and text.strip()
    ]

    dropped = []

    for text in sources:
        source_words = content_words(text)

        best_score, best_match = _best_match(source_words, targets)

        if best_score < RETENTION_THRESHOLD:
            dropped.append(
                {
                    "text": text,
                    "best_score": round(best_score, 3),
                    "best_match": best_match,
                }
            )

    retained = len(sources) - len(dropped)

    return {
        "input": len(sources),
        "retained": retained,
        "retention": round(retained / len(sources), 3),
        "dropped": dropped,
    }


def _best_match(
    source_words: set[str],
    targets: list[tuple[str, set[str]]],
) -> tuple[float, str | None]:
    """Best share of ``source_words`` covered by any single target."""
    if not source_words:
        return 0.0, None

    best_score = 0.0
    best_text = None

    for text, target_words in targets:
        score = len(source_words & target_words) / len(source_words)

        if score > best_score:
            best_score = score
            best_text = text

    return best_score, best_text


def _section_items(brd: object, section: str) -> list[str]:
    if not isinstance(brd, dict):
        return []

    content = brd.get(section)

    if not isinstance(content, dict):
        return []

    items = content.get("requirements")

    if not isinstance(items, list):
        return []

    return [item for item in items if isinstance(item, str)]


def _combined_retention(functional: dict, non_functional: dict) -> float | None:
    total_input = functional["input"] + non_functional["input"]

    if not total_input:
        return None

    total_retained = functional["retained"] + non_functional["retained"]

    return round(total_retained / total_input, 3)


def _empty_group() -> dict:
    return {
        "input": 0,
        "retained": 0,
        "retention": None,
        "dropped": [],
    }
