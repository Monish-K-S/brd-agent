"""M-2: Gmail/Drive imports must respect the extraction-size caps.

Two gaps used to let unbounded content into `standard_documents`:

* Gmail bodies arrived with no character ceiling at all (the upload path
  caps at `max_extracted_chars`, Gmail did not), and `content` is Postgres
  `Text` — unlimited.
* Drive buffered the whole file with a single `.execute()` *before* the
  size check, so an oversized or mis-declared file was fully resident in
  RAM before being rejected. It now streams and aborts past the ceiling.

A third gap covered here: the aggregate fed to the single project PDF sent
to Sarvam was unbounded (N docs x `max_extracted_chars`), so the extraction
service truncates the tail to fit `max_aggregate_chars`.
"""

import base64
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.core.config import settings
from app.ai.models.standard_document import (
    StandardDocument as AIStandardDocument,
)
from app.integrations.drive.service import DriveService
from app.integrations.gmail.import_service import GmailImportService
from app.services.document_extraction_service import (
    DocumentExtractionService,
)


def gmail_message(body: str) -> dict:
    """A Gmail `messages.get` payload with a text/plain body."""

    return {
        "id": "msg-1",
        "threadId": "thread-1",
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "Subject", "value": "Big email"}],
            "body": {
                "data": base64.urlsafe_b64encode(
                    body.encode("utf-8"),
                ).decode("ascii"),
            },
        },
    }


def gmail_import_service(monkeypatch, message: dict) -> GmailImportService:
    service = GmailImportService(db=SimpleNamespace())

    monkeypatch.setattr(
        service.document_repository,
        "get_by_gmail_message_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        service.gmail_service,
        "get_message",
        lambda **_kwargs: message,
    )

    return service


def test_gmail_oversized_message_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "max_extracted_chars", 10)

    service = gmail_import_service(
        monkeypatch,
        gmail_message("x" * 100),
    )

    with pytest.raises(ValueError, match="too large"):
        service.import_messages(
            workspace_id=uuid4(),
            user_id=uuid4(),
            message_ids=["msg-1"],
        )


def test_gmail_message_under_cap_imports(monkeypatch):
    monkeypatch.setattr(settings, "max_extracted_chars", 10_000)

    created = [SimpleNamespace(id=uuid4())]
    service = gmail_import_service(
        monkeypatch,
        gmail_message("short body"),
    )
    monkeypatch.setattr(
        service.document_service,
        "create_documents_from_ingestion",
        lambda **_kwargs: created,
    )

    documents, skipped = service.import_messages(
        workspace_id=uuid4(),
        user_id=uuid4(),
        message_ids=["msg-1"],
    )

    assert documents == created
    assert skipped == []


def drive_service(monkeypatch, downloader_cls) -> DriveService:
    service = DriveService(db=SimpleNamespace())

    # drive.files().get_media(fileId=...) -> a request object the fake
    # downloader ignores.
    drive_stub = SimpleNamespace(
        files=lambda: SimpleNamespace(
            get_media=lambda fileId: object(),
        ),
    )

    monkeypatch.setattr(
        service,
        "_drive_client",
        lambda _user_id: drive_stub,
    )
    monkeypatch.setattr(
        "app.integrations.drive.service.MediaIoBaseDownload",
        downloader_cls,
    )

    return service


class AbortDownloader:
    """Writes each planned chunk and never reports done.

    The download loop's only exit is therefore the byte ceiling, which is
    exactly what the abort test exercises.
    """

    def __init__(self, buffer, _request, chunksize=None):
        self.buffer = buffer
        self.plan = iter([600_000, 600_000])

    def next_chunk(self):
        self.buffer.write(b"x" * next(self.plan))

        return None, False


class ExactDownloader:
    """Writes 500k per chunk and reports done once the plan is exhausted."""

    def __init__(self, buffer, _request, chunksize=None):
        self.buffer = buffer
        self.count = 0

    def next_chunk(self):
        self.buffer.write(b"x" * 500_000)
        self.count += 1

        return None, self.count >= 2


def test_drive_download_aborts_past_ceiling(monkeypatch):
    service = drive_service(monkeypatch, AbortDownloader)

    with pytest.raises(ValueError, match="too large"):
        service.download_file(
            user_id=uuid4(),
            file_id="file-1",
            max_bytes=1_000_000,
        )


def test_drive_download_allows_up_to_the_ceiling(monkeypatch):
    service = drive_service(monkeypatch, ExactDownloader)

    result = service.download_file(
        user_id=uuid4(),
        file_id="file-1",
        max_bytes=1_000_000,
    )

    assert len(result) == 1_000_000


def _service_without_init() -> DocumentExtractionService:
    # _fit_to_aggregate_budget only needs settings + TRUNCATION_MARKER, so
    # skip the constructor (it builds repositories and the Sarvam extractor).
    return object.__new__(DocumentExtractionService)


def ai_document(content: str) -> AIStandardDocument:
    return AIStandardDocument(
        id=uuid4(),
        source_type="txt",
        content=content,
    )


def test_aggregate_budget_leaves_small_set_untouched():
    service = _service_without_init()
    documents = [ai_document("a" * 100), ai_document("b" * 100)]

    fitted = service._fit_to_aggregate_budget(documents)

    assert [d.content for d in fitted] == ["a" * 100, "b" * 100]


def test_aggregate_budget_truncates_the_crossing_document(monkeypatch):
    monkeypatch.setattr(settings, "max_aggregate_chars", 100)

    service = _service_without_init()
    documents = [
        ai_document("a" * 60),
        ai_document("b" * 60),
        ai_document("c" * 60),
    ]

    fitted = service._fit_to_aggregate_budget(documents)

    # Doc 1 fits whole; doc 2 is truncated with the marker; doc 3 is
    # dropped entirely and stays unextracted for a later run.
    assert fitted[0].content == "a" * 60
    assert fitted[1].content.startswith("b" * 40)
    assert DocumentExtractionService.TRUNCATION_MARKER in fitted[1].content
    assert len(fitted) == 2


def test_aggregate_budget_zero_drops_everything(monkeypatch):
    monkeypatch.setattr(settings, "max_aggregate_chars", 0)

    service = _service_without_init()

    assert service._fit_to_aggregate_budget([ai_document("a" * 10)]) == []
