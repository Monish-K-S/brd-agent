"""Assemble one evaluation record from a finished generation.

The input is exactly what the generation job already holds in memory when
it succeeds: the BRD dict, the consolidated knowledge dict, the phase
timings, and the generator's token usage. Nothing is re-read from the
database and no provider is called again, which is why this costs zero
extra API budget.

Every input is guarded rather than assumed. The callers include tests
that mock the whole pipeline, and a record with ``"available": false``
is a far better outcome than an exception inside a generation job.
"""

from datetime import datetime, timezone

from app.ai.mappers.document_knowledge_mapper import DocumentKnowledgeMapper
from app.evals.metrics.duplication import score_duplication
from app.evals.metrics.groundedness import score_groundedness
from app.evals.metrics.retention import score_retention
from app.evals.metrics.structure import score_structure

SCHEMA_VERSION = 1


def build_generation_eval(
    job_id: object,
    workspace_id: object,
    brd_data: object,
    knowledge_data: object,
    timings: dict | None = None,
    usage: object = None,
) -> dict:
    """Build the record for one successful generation."""
    knowledge = _to_knowledge(knowledge_data)

    structure = score_structure(brd_data)
    retention = score_retention(knowledge, brd_data)
    groundedness = score_groundedness(brd_data, knowledge)
    duplication = score_duplication(brd_data)

    return {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds",
        ),
        "job_id": str(job_id),
        "workspace_id": str(workspace_id),
        "timings": _clean_timings(timings),
        "usage": _clean_usage(usage),
        "metrics": {
            "structure": structure,
            "retention": retention,
            "groundedness": groundedness,
            "duplication": duplication,
        },
        "summary": {
            "valid": structure["valid"],
            "sections_present": structure["sections_present"],
            "retention": retention["overall_retention"],
            "unsupported_rate": groundedness["unsupported_rate"],
            "duplicate_items": duplication["duplicate_items"],
            "total_seconds": _total_seconds(timings),
        },
    }


def _to_knowledge(knowledge_data: object):
    """Map the stored knowledge dict to the dataclass the metrics expect.

    Returns ``None`` for anything that is not a dict, which the metrics
    already treat as "no reference answer available".
    """
    if not isinstance(knowledge_data, dict):
        return None

    try:
        return DocumentKnowledgeMapper().map(knowledge_data)
    except (AttributeError, TypeError, KeyError, ValueError):
        return None


def _clean_timings(timings: object) -> dict:
    if not isinstance(timings, dict):
        return {}

    return {
        name: round(float(value), 3)
        for name, value in timings.items()
        if isinstance(name, str)
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    }


def _clean_usage(usage: object) -> dict | None:
    """Accept only a real usage dict.

    The generation service exposes the generator through a cached
    property; tests mock the service, so this attribute can arrive as a
    MagicMock. Recording that would produce a record full of nonsense.
    """
    if not isinstance(usage, dict):
        return None

    return usage


def _total_seconds(timings: object) -> float | None:
    cleaned = _clean_timings(timings)

    if not cleaned:
        return None

    return round(sum(cleaned.values()), 3)
