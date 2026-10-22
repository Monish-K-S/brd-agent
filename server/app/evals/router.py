"""Dev-only endpoints for the evaluation harness.

Mounted through ``register_eval_routes`` rather than at import time so a
test can prove production adds zero routes without reimporting the app.
That is the property worth guarding: this is developer tooling, and the
only way it can hurt the product is by being reachable in production.

One endpoint here can spend money — ``POST /evals/run`` with ``replay``
false. Three things bound it: the production gate, the auth dependency,
and the coordinator's one-run-at-a-time slot.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth.current_user import get_current_db_user
from app.core.config import settings
from app.db.models.user import User
from app.evals import coordinator, store
from app.evals.verdict import evaluate_summary

router = APIRouter(
    prefix="/evals",
    tags=["Evaluations"],
)

# The listing is a table in a developer tool; loading every full record to
# render it would be wasteful, and the records are small but not free.
MAX_LISTED_RECORDS = 50


class EvalRunRequest(BaseModel):
    scenarios: list[str] = Field(
        default_factory=lambda: ["all"],
        description="Scenario names, or 'all'.",
    )
    replay: bool = Field(
        default=True,
        description=(
            "Reuse the cached extraction (free). Set false for a live run, "
            "which costs one Sarvam job per scenario."
        ),
    )


# ------------------------------------------------------- generation records


def _summary(record: dict) -> dict:
    summary = record.get("summary", {})

    return {
        "record_id": record.get("record_id"),
        "job_id": record.get("job_id"),
        "workspace_id": record.get("workspace_id"),
        "recorded_at": record.get("recorded_at"),
        "summary": summary,
        "usage": record.get("usage"),
        "verdict": evaluate_summary(summary),
    }


@router.get("/generations")
def list_generation_evals(
    current_user: User = Depends(get_current_db_user),
) -> dict:
    records = store.list_records(limit=MAX_LISTED_RECORDS)

    return {
        "count": len(records),
        "records": [_summary(record) for record in records],
    }


@router.get("/generations/{record_id}")
def get_generation_eval(
    record_id: str,
    current_user: User = Depends(get_current_db_user),
) -> dict:
    record = store.load_record(record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation record not found",
        )

    return record


# ------------------------------------------------------------- benchmarks


@router.get("/scenarios")
def list_benchmark_scenarios(
    current_user: User = Depends(get_current_db_user),
) -> dict:
    return {
        "scenarios": coordinator.scenario_catalogue(),
        "active_run": coordinator.active_run(),
    }


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
)
def start_benchmark_run(
    request: EvalRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_db_user),
) -> dict:
    if not request.scenarios:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No scenarios requested",
        )

    try:
        run_id = coordinator.start_run(
            scenario_names=list(request.scenarios),
            replay=request.replay,
        )
    except coordinator.RunBusyError as exc:
        # 409 rather than queueing: a second concurrent run would spend a
        # second batch of Sarvam jobs for the same answer.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    background_tasks.add_task(
        coordinator.execute_run,
        run_id,
        list(request.scenarios),
        request.replay,
    )

    return {
        "run_id": run_id,
        "status": coordinator.STATUS_RUNNING,
        "mode": "replay" if request.replay else "live",
    }


@router.get("/runs")
def list_benchmark_runs(
    current_user: User = Depends(get_current_db_user),
) -> dict:
    runs = coordinator.list_runs()

    return {
        "count": len(runs),
        "runs": runs,
        "active_run": coordinator.active_run(),
    }


@router.get("/runs/{run_id}")
def get_benchmark_run(
    run_id: str,
    current_user: User = Depends(get_current_db_user),
) -> dict:
    run = coordinator.load_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark run not found",
        )

    return run


@router.get("/runs/{run_id}/report.html")
def get_benchmark_report(
    run_id: str,
    current_user: User = Depends(get_current_db_user),
) -> FileResponse:
    path = coordinator.run_report_path(run_id)

    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return FileResponse(
        path=path,
        media_type="text/html",
        filename=f"brd-evaluation-{run_id}.html",
    )


def register_eval_routes(app, settings_obj=settings) -> bool:
    """Mount the evaluation routes unless this is production.

    Returns whether they were mounted, so startup can log it once instead
    of leaving a developer guessing why /evals 404s.
    """
    if settings_obj.environment == "production":
        return False

    if not settings_obj.eval_enabled:
        return False

    app.include_router(router)

    return True
