"""On-disk storage for generation evaluation records.

One JSON file per generation, named so that sorting by filename sorts by
time — no parsing needed to list or prune. Deliberately not a database
table: this is developer tooling, it must never require a migration, and
the product must keep working if the directory is deleted.

Nothing here raises on read. A corrupt or unreadable record is skipped
rather than allowed to break a listing, because the alternative is a
developer tool that takes down an endpoint.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("brd-agent.evals")

DEFAULT_KEEP = 50

# Record ids come from the URL, so they are validated before touching the
# filesystem. Dev-only is not a reason to allow traversal.
_RECORD_ID = re.compile(r"[0-9A-Za-z_-]{1,120}\Z")


def default_directory() -> Path:
    return Path(__file__).resolve().parent / "generations"


def save_record(
    record: dict,
    directory: str | Path | None = None,
    keep: int = DEFAULT_KEEP,
) -> str | None:
    """Write one record and prune the directory. Returns the record id.

    Returns ``None`` when the write fails: the caller is a generation
    job, and losing an evaluation record must never fail the job.
    """
    target = Path(directory) if directory is not None else default_directory()

    record_id = _record_id(record)

    if record_id is None:
        return None

    try:
        target.mkdir(parents=True, exist_ok=True)

        path = target / f"{record_id}.json"

        # Persisted with the id so a record read back from disk is
        # self-describing — the list endpoint never has to re-derive it
        # from the filename.
        stored = {**record, "record_id": record_id}

        path.write_text(
            json.dumps(stored, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        logger.warning(
            "Could not write evaluation record %s",
            record_id,
            exc_info=True,
        )

        return None

    prune(directory=target, keep=keep)

    return record_id


def list_records(
    directory: str | Path | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Return every readable record, newest first."""
    target = Path(directory) if directory is not None else default_directory()

    if not target.is_dir():
        return []

    records = []

    for path in sorted(target.glob("*.json"), reverse=True):
        record = _read(path)

        if record is not None:
            records.append(record)

        if limit is not None and len(records) >= limit:
            break

    return records


def load_record(
    record_id: str,
    directory: str | Path | None = None,
) -> dict | None:
    """Load one record by id, or ``None`` if it is missing or invalid."""
    if not is_valid_record_id(record_id):
        return None

    target = Path(directory) if directory is not None else default_directory()

    return _read(target / f"{record_id}.json")


def prune(
    directory: str | Path | None = None,
    keep: int = DEFAULT_KEEP,
) -> int:
    """Delete all but the newest ``keep`` records. Returns the count removed."""
    target = Path(directory) if directory is not None else default_directory()

    if keep < 1 or not target.is_dir():
        return 0

    paths = sorted(target.glob("*.json"), reverse=True)

    removed = 0

    for path in paths[keep:]:
        try:
            path.unlink()
            removed += 1
        except OSError:
            logger.warning(
                "Could not prune evaluation record %s",
                path.name,
                exc_info=True,
            )

    return removed


def is_valid_record_id(record_id: object) -> bool:
    return isinstance(record_id, str) and _RECORD_ID.fullmatch(record_id) is not None


def _record_id(record: dict) -> str | None:
    """``<UTC timestamp>-<job id>``, or None when the record is unusable."""
    job_id = record.get("job_id")

    if not isinstance(job_id, str) or not is_valid_record_id(job_id):
        return None

    return f"{_timestamp()}-{job_id}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


def _read(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "Skipping unreadable evaluation record %s",
            path.name,
            exc_info=True,
        )

        return None

    return payload if isinstance(payload, dict) else None
