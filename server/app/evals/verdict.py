"""Turn a generation's numbers into one plain-language verdict.

The dashboard shows a lot of figures; this decides whether any of them
warrant a second look, and says why in words. Kept server-side so the
client never invents thresholds — a verdict you cannot inspect is worse
than no verdict at all.

The thresholds are conventions chosen to be quiet, not measured failure
rates. They flag "check this", never "this is wrong".
"""

MIN_RETENTION = 0.85
MAX_UNTRACED_RATE = 0.15
MAX_REPEATED_ITEMS = 3

LEVEL_COMPLETE = "complete"
LEVEL_REVIEW = "review"


def evaluate_summary(summary: object) -> dict:
    """Return ``{"level", "reasons"}`` for one generation summary."""
    if not isinstance(summary, dict):
        return {"level": LEVEL_COMPLETE, "reasons": []}

    reasons = []

    sections = summary.get("sections_present")

    if isinstance(sections, int) and sections < 11:
        missing = 11 - sections

        reasons.append(
            f"{missing} {'section is' if missing == 1 else 'sections are'} empty"
        )

    retention = summary.get("retention")
    kept = summary.get("functional_retained")
    total = summary.get("functional_input")

    if isinstance(retention, (int, float)) and retention < MIN_RETENTION:
        if isinstance(kept, int) and isinstance(total, int) and total:
            reasons.append(
                f"{total - kept} of {total} requirements were not kept"
            )
        else:
            reasons.append(
                f"only {round(retention * 100)}% of requirements were kept"
            )

    unsupported = summary.get("unsupported_rate")

    if isinstance(unsupported, (int, float)) and unsupported > MAX_UNTRACED_RATE:
        reasons.append(
            f"{round(unsupported * 100)}% of lines could not be traced to your sources"
        )

    duplicates = summary.get("duplicate_items")

    if isinstance(duplicates, int) and duplicates >= MAX_REPEATED_ITEMS:
        reasons.append(f"{duplicates} lines are repeated")

    return {
        "level": LEVEL_REVIEW if reasons else LEVEL_COMPLETE,
        "reasons": reasons,
    }
