"""Retention metric — did the BRD keep every requirement it was given?

This is the highest-value automatic check. The generation prompt tells
the model that "every functional requirement from ProjectKnowledge must
remain represented unless it is genuinely duplicated without loss of
meaning", so the failure it guards against is silent: fifteen extracted
requirements go in, nine come out, and nothing in the pipeline notices.

No ground truth is needed — the input knowledge *is* the reference — which
is why this can run on every real generation for free.

**Matching against the whole document, not one section.** Two earlier
versions of this metric were wrong in ways only real data exposed:

* scoping to a single section reported legitimate re-homing as a loss;
* restricting to the requirement sections still missed requirements the
  model placed in ``scope``, ``assumptions`` or ``decisions`` — which is
  a perfectly sensible place for a constraint.

"Represented" means present anywhere in the document. A requirement that
appears nowhere has genuinely been lost, and that is the only thing this
metric now claims.
"""

from app.evals.models import iter_brd_text_items
from app.evals.text import content_words

RETENTION_THRESHOLD = 0.6

# A requirement of one or two content words cannot lose a word and still
# mean the same thing: "password" matching "reset" tells you nothing.
# Sampled from a real workspace, where Sarvam extracted *noun phrases*
# ("CSV exports", "dashboard reporting") rather than the full sentences
# the benchmark scenarios produce — every one of those scored at or below
# 0.5 against a correct BRD and was reported as dropped.
SHORT_REQUIREMENT_WORDS = 2
# Two of three words. Written as a division, not 0.67, because
# 0.67 > 2/3 and that rounding decided a real verdict.
THREE_WORD_THRESHOLD = 2 / 3


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

    targets = [
        (section, text, _stemmed_words(text))
        for section, text in iter_brd_text_items(brd)
    ]

    functional = _score_group(
        source_texts=[
            getattr(item, "description", "")
            for item in getattr(knowledge, "functional_requirements", [])
        ],
        targets=targets,
    )

    non_functional = _score_group(
        source_texts=[
            getattr(item, "description", "")
            for item in getattr(knowledge, "non_functional_requirements", [])
        ],
        targets=targets,
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
    targets: list[tuple[str, str, set[str]]],
) -> dict:
    """Score one requirement group.

    ``retention`` is ``None`` when there was nothing to check. That is not
    the same as 1.0: "no requirements were extracted" is an input problem,
    and reporting it as perfect would hide it.

    Scoring is corpus coverage — how much of the requirement's vocabulary
    survives *somewhere* — while ``best_match`` names the closest single
    line so a finding stays explainable. Surface-form comparison alone
    scored "is converted into a ticket" against "shall automatically
    convert emails ... into new tickets" at 0.5 and called it lost.
    """
    sources = [
        text
        for text in source_texts
        if isinstance(text, str) and text.strip()
    ]

    if not sources:
        return _empty_group()

    corpus: set[str] = set()

    for _, _, words in targets:
        corpus |= words

    dropped = []

    for text in sources:
        source_words = _stemmed_words(text)

        if not source_words:
            continue

        coverage = len(source_words & corpus) / len(source_words)

        if coverage < _threshold(len(source_words)):
            best_score, best_match, best_section = _best_match(
                source_words,
                targets,
            )

            dropped.append(
                {
                    "text": text,
                    "score": round(coverage, 3),
                    "best_score": round(best_score, 3),
                    "best_match": best_match,
                    "best_section": best_section,
                    "missing_terms": sorted(source_words - corpus)[:5],
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
    targets: list[tuple[str, str, set[str]]],
) -> tuple[float, str | None, str | None]:
    """Closest single line, for explaining a finding rather than scoring it."""
    if not source_words:
        return 0.0, None, None

    best_score = 0.0
    best_text = None
    best_section = None

    for section, text, target_words in targets:
        score = len(source_words & target_words) / len(source_words)

        if score > best_score:
            best_score = score
            best_text = text
            best_section = section

    return best_score, best_text, best_section


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


def _stemmed_words(text: str) -> set[str]:
    return {_stem(word) for word in content_words(text)}


def _threshold(word_count: int) -> float:
    """Coverage a requirement must reach to count as retained."""
    if word_count <= SHORT_REQUIREMENT_WORDS:
        return 1.0

    if word_count == 3:
        return THREE_WORD_THRESHOLD

    return RETENTION_THRESHOLD


# Longest first, so "ations" is tried before "s".
_SUFFIXES = (
    "ations",
    "ation",
    "ements",
    "ement",
    "ments",
    "ment",
    "ings",
    "ing",
    "ions",
    "ion",
    "ities",
    "ity",
    "nesses",
    "ness",
    "ances",
    "ance",
    "ences",
    "ence",
    "edly",
    "ly",
    "ed",
    "es",
    "s",
)


def _stem(word: str) -> str:
    """Crude suffix stripping, deliberately not a real stemmer.

    Exists so ``converted``/``convert``, ``tickets``/``ticket`` and — the
    case that actually broke on real data — ``creation``/``create`` and
    ``invitations``/``invite`` compare equal. Two passes because the
    second suffix is only visible after the first is removed
    (``creates`` -> ``create`` -> ``creat``).

    It never touches the first characters, so two requirements that
    differ in their distinctive word still differ.
    """
    for _ in range(2):
        for suffix in _SUFFIXES:
            if not word.endswith(suffix):
                continue

            remainder = word[: -len(suffix)]

            # Keep at least four characters, except for short words where
            # an aggressive cut is the only way "ratings" and "rate" meet.
            # Scanning continues past a rejected suffix instead of
            # stopping: "creation" has to fall through "ation" (which
            # would leave "cre") to "ion" (which leaves "creat").
            short_cut = (
                len(suffix) >= 3
                and len(word) <= 7
                and len(remainder) >= 3
            )

            if len(remainder) >= 4 or short_cut:
                word = remainder

                break
        else:
            break

    # "create" and "creation" only both reach "creat" if the trailing e
    # goes too. Three characters is the floor, again to avoid shredding.
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]

    return word
