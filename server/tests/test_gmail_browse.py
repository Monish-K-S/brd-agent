"""Gmail browse batching (L-9).

The recent/search routes used to fetch message details one id at a time —
each call re-read credentials (DB + Fernet, sometimes a refresh) and
rebuilt the discovery client, so a 20-result search cost 21 serial HTTP
round trips plus 42 setup calls. `GmailService.get_messages` must build
once, batch every `messages.get` into a single HTTP round trip, preserve
input order, propagate a failed sub-response (400 parity), and degrade to
sequential GETs on the same built client when the batch itself fails.

The Google client is faked here; only `googleapiclient.discovery.build`
is monkeypatched (the service imports it inside the method, at call time).
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.integrations.gmail.service import GmailService


class Harness:
    """Counts every boundary the old N+1 code crossed."""

    def __init__(self):
        self.credential_reads = 0
        self.builds = 0
        self.batch_executes = 0
        self.batch_added: list[str] = []
        self.sequential_executes = 0
        self.fail_batch = False
        self.fail_ids: set[str] = set()
        self._callback = None

    @staticmethod
    def payload(message_id: str) -> dict:
        return {"id": message_id}


class FakeGetRequest:
    """One sequential `messages.get(...)` — `.execute()` is one HTTP call."""

    def __init__(self, harness: Harness, message_id: str):
        self.harness = harness
        self.message_id = message_id

    def execute(self):
        self.harness.sequential_executes += 1

        return self.harness.payload(self.message_id)


class FakeBatch:
    def __init__(self, harness: Harness, callback):
        self.harness = harness
        self.callback = callback
        self.message_ids: list[str] = []

    def add(self, request, request_id=None):
        self.message_ids.append(request_id)
        self.harness.batch_added.append(request_id)

    def execute(self):
        self.harness.batch_executes += 1

        if self.harness.fail_batch:
            raise RuntimeError("batch endpoint exploded")

        # Emulate the googleapiclient callback contract:
        # callback(request_id, response, exception).
        for message_id in self.message_ids:
            if message_id in self.harness.fail_ids:
                self.callback(
                    message_id,
                    None,
                    RuntimeError(f"boom:{message_id}"),
                )
            else:
                self.callback(
                    message_id,
                    self.harness.payload(message_id),
                    None,
                )


class FakeMessages:
    def __init__(self, harness: Harness):
        self.harness = harness

    def get(self, userId=None, id=None, format=None):
        return FakeGetRequest(self.harness, id)


class FakeUsers:
    def __init__(self, harness: Harness):
        self.harness = harness

    def messages(self):
        return FakeMessages(self.harness)


class FakeGmail:
    def __init__(self, harness: Harness):
        self.harness = harness

    def users(self):
        return FakeUsers(self.harness)

    def new_batch_http_request(self, callback=None):
        self.harness._callback = callback

        return FakeBatch(self.harness, callback)


@pytest.fixture
def harness() -> Harness:
    return Harness()


@pytest.fixture
def gmail_service(harness: Harness, monkeypatch) -> GmailService:
    service = GmailService(db=SimpleNamespace())

    def read_credentials(user_id):
        harness.credential_reads += 1

        return object()

    monkeypatch.setattr(service, "get_credentials", read_credentials)

    def fake_build(api, version, credentials=None):
        harness.builds += 1

        return FakeGmail(harness)

    monkeypatch.setattr(
        "googleapiclient.discovery.build",
        fake_build,
    )

    return service


def test_get_messages_batches_into_one_round_trip(
    gmail_service,
    harness,
):
    message_ids = [f"m{index}" for index in range(20)]

    result = gmail_service.get_messages(
        user_id=uuid4(),
        message_ids=message_ids,
    )

    # The N+1 is gone: one credential read, one client build, one batch.
    assert harness.credential_reads == 1
    assert harness.builds == 1
    assert harness.batch_executes == 1
    assert harness.sequential_executes == 0
    assert harness.batch_added == message_ids

    # Input order is preserved regardless of callback arrival.
    assert [message["id"] for message in result] == message_ids


def test_get_messages_falls_back_when_batch_fails(
    gmail_service,
    harness,
):
    harness.fail_batch = True
    message_ids = [f"m{index}" for index in range(7)]

    result = gmail_service.get_messages(
        user_id=uuid4(),
        message_ids=message_ids,
    )

    # Batch trouble degrades to slower, not broken — and still one client
    # build and one credential read for the whole fallback.
    assert harness.batch_executes == 1
    assert harness.sequential_executes == len(message_ids)
    assert harness.builds == 1
    assert harness.credential_reads == 1
    assert [message["id"] for message in result] == message_ids


def test_get_messages_propagates_failed_sub_response(
    gmail_service,
    harness,
):
    harness.fail_ids = {"m3"}
    message_ids = [f"m{index}" for index in range(5)]

    # The old per-id loop raised on the failing get (routes map it to 400);
    # the batch must surface the same failure instead of silently skipping.
    with pytest.raises(RuntimeError, match="boom:m3"):
        gmail_service.get_messages(
            user_id=uuid4(),
            message_ids=message_ids,
        )

    assert harness.sequential_executes == 0


def test_get_messages_empty_list_builds_nothing(
    gmail_service,
    harness,
):
    result = gmail_service.get_messages(
        user_id=uuid4(),
        message_ids=[],
    )

    assert result == []
    assert harness.credential_reads == 0
    assert harness.builds == 0
    assert harness.batch_executes == 0
