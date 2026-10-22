"""Run lifecycle for the benchmark: start, track, list, load.

Kept out of the router so the whole thing is testable without HTTP, and
so the one rule that matters — **one run at a time** — has exactly one
implementation.

The concurrency guard is a timestamped slot rather than a bare
``threading.Lock``. A lock acquired by a request whose background task
never runs would be held until the process restarts, permanently
disabling the endpoint; a slot older than ``STALE_SECONDS`` is treated as
abandoned and can be superseded. The same rule is what lets the UI mark a
run as interrupted after a restart instead of spinning forever.
"""

import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from app.evals.datasets import LEVEL_ORDER, list_scenarios, load_scenario, ordered_scenarios
from app.evals.report import build_run, write_run
from app.evals.runner import (
    MODE_LIVE,
    MODE_REPLAY,
    RunConfig,
    _cache_path,
    run_scenario,
)

RUNS_DIR = Path(__file__).resolve().parent / "reports"

# A live run of four scenarios takes ~2 minutes. Fifteen minutes means a
# run is only considered abandoned when it plausibly is.
STALE_SECONDS = 15 * 60

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_RUN_ID = re.compile(r"[0-9A-Za-z_-]{1,120}\Z")

_state_lock = threading.Lock()
_active: dict | None = None


class RunBusyError(RuntimeError):
    """A benchmark run is already in progress."""


def is_valid_run_id(run_id: object) -> bool:
    return isinstance(run_id, str) and _RUN_ID.fullmatch(run_id) is not None


def active_run() -> dict | None:
    """The run currently in progress, or None. Ignores abandoned slots."""
    with _state_lock:
        return _usable_active()


def start_run(scenario_names: list[str], replay: bool) -> str:
    """Claim the run slot and return a new run id.

    Raises ``RunBusyError`` if another run is in progress — the caller
    turns that into a 409 rather than starting a second Sarvam batch.
    """
    global _active

    with _state_lock:
        if _usable_active() is not None:
            raise RunBusyError("A benchmark run is already in progress")

        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")

        _active = {"run_id": run_id, "started_at": time.monotonic()}

    return run_id


def execute_run(run_id: str, scenario_names: list[str], replay: bool) -> None:
    """Run the benchmark. Intended for a background task; never raises."""
    try:
        if "all" in scenario_names:
            scenario_names = [item.name for item in ordered_scenarios()]

        _write_status(
            run_id,
            status=STATUS_RUNNING,
            mode=MODE_REPLAY if replay else MODE_LIVE,
            index=0,
            total=len(scenario_names),
            scenario=None,
        )

        scenarios = [load_scenario(name) for name in scenario_names]

        config = RunConfig(mode=MODE_REPLAY if replay else MODE_LIVE)

        results = []

        for index, scenario in enumerate(scenarios, start=1):
            _write_status(
                run_id,
                status=STATUS_RUNNING,
                mode=config.mode,
                index=index,
                total=len(scenarios),
                scenario=scenario.name,
            )

            results.append(
                run_scenario(scenario, config).to_dict(),
            )

        run = build_run(
            run_id,
            results,
            mode=config.mode,
            config={
                "model": None,
                "thinking_budget": None,
                "dedupe": True,
                "repeats": 1,
            },
        )

        write_run(run, RUNS_DIR / run_id)

        _write_status(
            run_id,
            status=STATUS_COMPLETED,
            mode=config.mode,
            index=len(scenarios),
            total=len(scenarios),
            scenario=None,
        )
    except Exception as exc:  # noqa: BLE001 — recorded, never raised
        _write_status(
            run_id,
            status=STATUS_FAILED,
            mode=MODE_REPLAY if replay else MODE_LIVE,
            index=0,
            total=len(scenario_names),
            scenario=None,
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        _release(run_id)


def list_runs(limit: int = 25) -> list[dict]:
    """Every run directory, newest first, with a status for each."""
    if not RUNS_DIR.is_dir():
        return []

    runs = []

    for directory in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not directory.is_dir():
            continue

        entry = load_run(directory.name)

        if entry is not None:
            runs.append(entry)

        if len(runs) >= limit:
            break

    return runs


def load_run(run_id: str) -> dict | None:
    """Status plus results for one run, or None if it does not exist."""
    if not is_valid_run_id(run_id):
        return None

    directory = RUNS_DIR / run_id

    if not directory.is_dir():
        return None

    status = _read_json(directory / "status.json")
    results = _read_json(directory / "results.json")

    if status is None and results is None:
        return None

    # Runs created by the CLI have no status file; derive one so they
    # appear in the same list instead of being invisible.
    if status is None:
        status = {
            "run_id": run_id,
            "status": STATUS_COMPLETED,
            "mode": (results or {}).get("mode"),
            "started_at": (results or {}).get("started_at"),
            "updated_at": (results or {}).get("finished_at"),
        }

    entry = dict(status)

    entry["run_id"] = run_id
    entry["result_available"] = results is not None
    entry["stale"] = _is_stale(status)

    if results is not None:
        entry["scenarios"] = [
            {
                "scenario": item.get("scenario"),
                "summary": item.get("summary_median", {}),
                "timings": item.get("timing_median", {}),
            }
            for item in results.get("scenarios", [])
        ]

    return entry


def run_report_path(run_id: str) -> Path | None:
    if not is_valid_run_id(run_id):
        return None

    path = RUNS_DIR / run_id / "report.html"

    return path if path.is_file() else None


def scenario_catalogue() -> list[dict]:
    """Scenario metadata for the picker, ordered small → medium → large.

    Reads disk only — no network.
    """
    catalogue = []

    for name in list_scenarios():
        scenario = load_scenario(name)

        catalogue.append(
            {
                "name": name,
                "level": scenario.level,
                "facts": len(scenario.facts),
                "documents": len(scenario.inputs),
                "chars": scenario.total_chars,
                "cached": _cache_path(
                    scenario,
                    RunConfig(),
                ).is_file(),
            }
        )

    return sorted(
        catalogue,
        key=lambda item: (LEVEL_ORDER.get(item["level"], len(LEVEL_ORDER)), item["name"]),
    )


# ------------------------------------------------------------------ state


def _usable_active() -> dict | None:
    """The active slot, unless it has gone quiet for too long."""
    if _active is None:
        return None

    if time.monotonic() - _active["started_at"] > STALE_SECONDS:
        return None

    return _active


def _release(run_id: str) -> None:
    global _active

    with _state_lock:
        if _active is not None and _active["run_id"] == run_id:
            _active = None


def _write_status(
    run_id: str,
    *,
    status: str,
    mode: str,
    index: int,
    total: int,
    scenario: str | None,
    error: str | None = None,
) -> None:
    directory = RUNS_DIR / run_id

    try:
        directory.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": run_id,
            "status": status,
            "mode": mode,
            "index": index,
            "total": total,
            "scenario": scenario,
            "error": error,
            "started_at": _now(),
        }

        (directory / "status.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # A status file is a convenience; failing to write one must not
        # turn a successful benchmark into a failed one.
        pass


def _is_stale(status: dict) -> bool:
    """A run still marked running well after it started was interrupted.

    This is what a backend restart mid-run looks like: the in-memory slot
    is gone, so nothing will ever update the file.
    """
    if status.get("status") != STATUS_RUNNING:
        return False

    updated = status.get("started_at")

    if not isinstance(updated, str):
        return False

    try:
        seen = datetime.fromisoformat(updated)
    except ValueError:
        return False

    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)

    return (datetime.now(timezone.utc) - seen).total_seconds() > STALE_SECONDS


def _read_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def reset_for_tests() -> None:
    """Clear the in-memory slot. Tests only — never called by the app."""
    global _active

    with _state_lock:
        _active = None
