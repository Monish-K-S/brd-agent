"""Dev-only read endpoints for generation evaluation records.

Mounted through ``register_eval_routes`` rather than at import time so a
test can prove production adds zero routes without reimporting the app.
That is the property worth guarding: this is a developer tool, and the
only way it can hurt the product is by being reachable in production.

Read-only on purpose. Runs are triggered by actually generating a BRD
(and, later, by the benchmark CLI), so there is no endpoint here that
can spend API budget.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.current_user import get_current_db_user
from app.core.config import settings
from app.db.models.user import User
from app.evals import store

router = APIRouter(
    prefix="/evals",
    tags=["Evaluations"],
)

# The listing is a table in a developer tool; loading every full record to
# render it would be wasteful, and the records are small but not free.
MAX_LISTED_RECORDS = 50


def _summary(record: dict) -> dict:
    return {
        "record_id": record.get("record_id"),
        "job_id": record.get("job_id"),
        "workspace_id": record.get("workspace_id"),
        "recorded_at": record.get("recorded_at"),
        "summary": record.get("summary", {}),
        "usage": record.get("usage"),
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
