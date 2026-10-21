"""Upload parse timing (P-6).

Parsing runs *inside* the upload request, so a request can spend up to
`max_upload_files` parses before it responds. Until this instrumentation
existed there was no way to tell a slow parse from a slow network, which
is why P-6 could only ever be argued structurally.

These tests pin the log contract only — not any duration, which would be
flaky. The numbers themselves are recorded in `ISSUES.md` §5g.
"""

import logging

import pytest

from app.services.document_ingestion_service import (
    DocumentIngestionService,
)


LOGGER = "brd-agent.ingestion"


@pytest.fixture
def text_file(tmp_path):
    path = tmp_path / "requirements.txt"
    path.write_text(
        "The system shall let users sign in with Google.\n"
        "Sessions expire after 30 minutes.\n",
        encoding="utf-8",
    )

    return path


def test_ingest_logs_parse_timing(caplog, text_file):
    with caplog.at_level(logging.INFO, logger=LOGGER):
        documents = DocumentIngestionService().ingest(text_file)

    assert documents

    records = [r for r in caplog.records if r.name == LOGGER]

    assert len(records) == 1

    message = records[0].getMessage()

    assert "parsed .txt in" in message
    assert "1 document(s)" in message
    # The character count is what makes a slow parse explainable: a
    # 200-page PDF and a 2-line txt differ by orders of magnitude.
    assert f"{len(documents[0].content)} chars" in message


def test_ingest_logs_one_line_per_file(caplog, text_file):
    service = DocumentIngestionService()

    with caplog.at_level(logging.INFO, logger=LOGGER):
        service.ingest(text_file)
        service.ingest(text_file)

    records = [r for r in caplog.records if r.name == LOGGER]

    # One record per file — not per page, not per document.
    assert len(records) == 2


def test_ingest_still_raises_for_unsupported_files(tmp_path, caplog):
    path = tmp_path / "unsupported.xyz"
    path.write_text("hello", encoding="utf-8")

    with caplog.at_level(logging.INFO, logger=LOGGER):
        with pytest.raises(ValueError):
            DocumentIngestionService().ingest(path)

    # A rejected file must not claim to have been parsed.
    assert [r for r in caplog.records if r.name == LOGGER] == []
