"""Latency metric — where the wall-clock time actually went.

The generation job already logs one line per phase, but logs are not
data: you cannot median them, chart them, or compare two runs without
reading them by hand. This turns the same numbers into a summary.

Repeats matter more here than anywhere else, because both remote calls
are variable. A single run reports ``n: 1`` so nobody mistakes it for a
distribution.
"""

from statistics import median


def summarise_latency(rows: list[dict]) -> dict:
    """Summarise per-phase seconds across one or more runs.

    Each row is ``{phase_name: seconds}``. The ``total`` entry is the
    per-run sum of that row's phases, so it stays comparable when a run
    skips a phase (a regeneration with no new sources has no extraction
    step and must not be reported as instant).
    """
    usable_rows = [row for row in rows if isinstance(row, dict)]

    if not usable_rows:
        return {}

    phases = sorted(
        {
            phase
            for row in usable_rows
            for phase, value in row.items()
            if _is_number(value)
        }
    )

    summary = {
        phase: _stats(
            [
                float(row[phase])
                for row in usable_rows
                if _is_number(row.get(phase))
            ]
        )
        for phase in phases
    }

    summary = {
        phase: stats
        for phase, stats in summary.items()
        if stats is not None
    }

    totals = [
        sum(
            float(value)
            for value in row.values()
            if _is_number(value)
        )
        for row in usable_rows
    ]

    total_stats = _stats(totals)

    if total_stats is not None:
        summary["total"] = total_stats

    return summary


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _stats(values: list[float]) -> dict | None:
    if not values:
        return None

    return {
        "n": len(values),
        "median": round(median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }
