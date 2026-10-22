"""K7 — dev-only benchmark triggers and dashboard endpoints.

Every route test patches ``coordinator.execute_run``. That is not
cosmetic: ``TestClient`` runs background tasks synchronously, so an
unpatched POST would perform a real benchmark — and a live one spends
Sarvam credits — inside the test suite.

No network, no DB, no provider calls.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.evals import coordinator


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(coordinator, "RUNS_DIR", tmp_path / "reports")
    coordinator.reset_for_tests()

    yield tmp_path / "reports"

    coordinator.reset_for_tests()


@pytest.fixture
def no_execution(monkeypatch):
    """Keep POST /evals/run from doing any work."""
    calls = []

    def fake_execute(run_id, scenario_names, replay):
        calls.append(
            {
                "run_id": run_id,
                "scenarios": scenario_names,
                "replay": replay,
            }
        )

    monkeypatch.setattr(coordinator, "execute_run", fake_execute)

    return calls


def _client():
    from app.auth.current_user import get_current_db_user
    from app.main import app

    app.dependency_overrides[get_current_db_user] = lambda: SimpleNamespace(
        id=uuid4(),
    )

    return app, TestClient(app)


def _get(path):
    app, client = _client()

    try:
        return client.get(path)
    finally:
        app.dependency_overrides.clear()


def _post(path, payload):
    app, client = _client()

    try:
        return client.post(path, json=payload)
    finally:
        app.dependency_overrides.clear()


# ------------------------------------------------------------- scenarios


def test_scenarios_endpoint_lists_the_catalogue():
    response = _get("/evals/scenarios")

    assert response.status_code == 200

    names = {item["name"] for item in response.json()["scenarios"]}

    assert {"library-rooms", "clinic-booking", "helpdesk-migration"} <= names

    catalogue = response.json()["scenarios"]

    small = next(item for item in catalogue if item["name"] == "library-rooms")

    assert small["level"] == "small"
    assert small["facts"] == 8
    assert small["documents"] == 1
    assert isinstance(small["cached"], bool)

    # Ordered least to most source material, so the picker reads as a
    # progression rather than alphabetically.
    levels = [item["level"] for item in catalogue]

    assert levels == sorted(levels, key=["small", "medium", "large"].index)

    facts = [item["facts"] for item in catalogue]
    documents = [item["documents"] for item in catalogue]

    assert facts == sorted(facts)
    assert documents == sorted(documents)


# --------------------------------------------------------------- running


def test_start_run_returns_202_and_schedules_the_work(runs_dir, no_execution):
    response = _post(
        "/evals/run",
        {"scenarios": ["library-rooms"], "replay": True},
    )

    assert response.status_code == 202

    payload = response.json()

    assert payload["status"] == "running"
    assert payload["mode"] == "replay"
    # TestClient runs background tasks inline, so this proves the task was
    # registered and what it received.
    assert no_execution == [
        {
            "run_id": payload["run_id"],
            "scenarios": ["library-rooms"],
            "replay": True,
        }
    ]


def test_a_second_run_while_busy_is_rejected(runs_dir, no_execution):
    first = _post("/evals/run", {"scenarios": ["library-rooms"], "replay": True})

    assert first.status_code == 202

    second = _post("/evals/run", {"scenarios": ["library-rooms"], "replay": True})

    # 409, not a queue: a second concurrent run would spend a second batch
    # of Sarvam jobs for the same answer.
    assert second.status_code == 409
    assert "already in progress" in second.json()["detail"]

    coordinator.reset_for_tests()


def test_empty_scenario_list_is_rejected(runs_dir, no_execution):
    response = _post("/evals/run", {"scenarios": [], "replay": True})

    assert response.status_code == 422


def test_busy_slot_is_released_when_the_run_finishes(runs_dir, monkeypatch):
    monkeypatch.setattr(
        coordinator,
        "load_scenario",
        lambda name: SimpleNamespace(name=name, level="small"),
    )
    monkeypatch.setattr(
        coordinator,
        "run_scenario",
        lambda scenario, config: MagicMock(
            to_dict=lambda: _result(scenario.name),
        ),
    )

    run_id = coordinator.start_run(["library-rooms"], replay=True)

    coordinator.execute_run(run_id, ["library-rooms"], replay=True)

    # The slot must not stay claimed, or the endpoint is dead until restart.
    assert coordinator.active_run() is None

    assert coordinator.start_run(["library-rooms"], replay=True) != run_id


def test_failure_records_the_error_and_still_releases_the_slot(
    runs_dir,
    monkeypatch,
):
    monkeypatch.setattr(
        coordinator,
        "load_scenario",
        lambda name: SimpleNamespace(name=name, level="small"),
    )

    def explode(scenario, config):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(coordinator, "run_scenario", explode)

    run_id = coordinator.start_run(["library-rooms"], replay=True)

    coordinator.execute_run(run_id, ["library-rooms"], replay=True)

    status = json.loads((runs_dir / run_id / "status.json").read_text())

    assert status["status"] == "failed"
    assert "provider exploded" in status["error"]

    assert coordinator.active_run() is None


def test_completed_run_writes_status_and_results(runs_dir, monkeypatch):
    monkeypatch.setattr(
        coordinator,
        "load_scenario",
        lambda name: SimpleNamespace(name=name, level="small"),
    )
    monkeypatch.setattr(
        coordinator,
        "run_scenario",
        lambda scenario, config: MagicMock(
            to_dict=lambda: _result(scenario.name),
        ),
    )

    run_id = coordinator.start_run(["library-rooms"], replay=True)

    coordinator.execute_run(run_id, ["library-rooms"], replay=True)

    directory = runs_dir / run_id

    assert (directory / "status.json").is_file()
    assert (directory / "results.json").is_file()
    assert (directory / "report.html").is_file()

    assert json.loads((directory / "status.json").read_text())["status"] == (
        "completed"
    )


# ---------------------------------------------------------------- reading


def test_runs_endpoint_lists_newest_first(runs_dir, no_execution):
    for name in ("20260101T000000000000", "20260102T000000000000"):
        directory = runs_dir / name
        directory.mkdir(parents=True)
        (directory / "results.json").write_text(
            json.dumps(
                {
                    "run_id": name,
                    "mode": "live",
                    "scenarios": [],
                    "started_at": "2026-01-01T00:00:00+00:00",
                    "finished_at": "2026-01-01T00:01:00+00:00",
                }
            ),
            encoding="utf-8",
        )

    response = _get("/evals/runs")

    assert response.status_code == 200

    ids = [run["run_id"] for run in response.json()["runs"]]

    assert ids == ["20260102T000000000000", "20260101T000000000000"]


def test_cli_runs_without_a_status_file_still_appear(runs_dir):
    # The CLI writes results.json only. It must not be invisible here.
    directory = runs_dir / "20260103T000000000000"
    directory.mkdir(parents=True)
    (directory / "results.json").write_text(
        json.dumps({"run_id": "x", "mode": "live", "scenarios": []}),
        encoding="utf-8",
    )

    run = coordinator.load_run("20260103T000000000000")

    assert run["status"] == "completed"
    assert run["result_available"] is True


def test_interrupted_run_is_marked_stale(runs_dir):
    # What a backend restart mid-run looks like: the in-memory slot is
    # gone, so nothing will ever update this file.
    directory = runs_dir / "20260101T000000000000"
    directory.mkdir(parents=True)
    (directory / "status.json").write_text(
        json.dumps(
            {
                "run_id": "20260101T000000000000",
                "status": "running",
                "started_at": "2020-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    run = coordinator.load_run("20260101T000000000000")

    assert run["status"] == "running"
    assert run["stale"] is True


def test_unknown_run_is_404(runs_dir):
    assert _get("/evals/runs/does-not-exist").status_code == 404


def test_report_is_served_as_html(runs_dir):
    directory = runs_dir / "20260101T000000000000"
    directory.mkdir(parents=True)
    (directory / "report.html").write_text(
        "<!doctype html><title>report</title>",
        encoding="utf-8",
    )

    response = _get("/evals/runs/20260101T000000000000/report.html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_report_path_traversal_is_rejected(runs_dir):
    assert coordinator.run_report_path("../../etc/passwd") is None
    assert _get("/evals/runs/..%2F..%2Fetc%2Fpasswd/report.html").status_code == 404


def test_missing_report_is_404(runs_dir):
    directory = runs_dir / "20260101T000000000000"
    directory.mkdir(parents=True)
    (directory / "results.json").write_text("{}", encoding="utf-8")

    assert _get("/evals/runs/20260101T000000000000/report.html").status_code == 404


def _result(name):
    return {
        "scenario": name,
        "mode": "replay",
        "timings": {"generation": 1.0},
        "usage": None,
        "metrics": {"coverage": {"missed": []}},
        "summary": {
            "valid": True,
            "recall": 1.0,
            "retention": 1.0,
            "unsupported_rate": 0.0,
            "duplicate_items": 0,
            "sections_present": 11,
            "total_seconds": 1.0,
        },
    }
