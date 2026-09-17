import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("brd-agent.audit")


def _serialize(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def audit(
    event: str,
    outcome: str,
    user_id: UUID | str | None = None,
    workspace_id: UUID | str | None = None,
    extra: dict | None = None,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "outcome": outcome,
        "user_id": _serialize(user_id) if user_id is not None else None,
        "workspace_id": (
            _serialize(workspace_id) if workspace_id is not None else None
        ),
    }

    if extra:
        record["extra"] = {
            key: _serialize(value) for key, value in extra.items()
        }

    logger.info(json.dumps(record))


class AuditMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)

            return

        if scope.get("path", "").startswith("/health"):
            await self.app(scope, receive, send)

            return

        start = time.perf_counter()
        status_code = 500

        async def send_with_capture(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            await send(message)

        try:
            await self.app(scope, receive, send_with_capture)
        finally:
            latency_ms = round(
                (time.perf_counter() - start) * 1000,
                1,
            )

            audit(
                event="http.request",
                outcome="success" if status_code < 400 else "error",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                },
            )
