"""Hard-block dedup: workspace names + document upload triple.

Workspace names are unique per user (case-insensitive, stripped).
Uploads are blocked when (file name, extension, byte size) matches a
stored document or repeats in-batch. File-name case is significant:
Spec.pdf vs spec.pdf are different files.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

import app.db.models.google_connection  # noqa: F401 — registers mapper
from app.api.routes.standard_document import (
    find_duplicate_upload,
    stored_document_key,
    upload_file_key,
)
from app.schemas.workspace import WorkspaceCreate
from app.services.workspace_service import (
    DuplicateWorkspaceError,
    WorkspaceService,
)


def test_workspace_name_stripped():
    workspace = WorkspaceCreate(name="  My project  ")

    assert workspace.name == "My project"


def test_workspace_name_blank_rejected():
    with pytest.raises(Exception):
        WorkspaceCreate(name="   ")


def test_workspace_name_too_long_rejected():
    with pytest.raises(Exception):
        WorkspaceCreate(name="x" * 201)


def test_workspace_duplicate_blocked():
    service = WorkspaceService(MagicMock())
    user_id = uuid4()

    service.workspace_repository.get_by_user_id_and_name = MagicMock(
        return_value=MagicMock(),
    )

    with pytest.raises(DuplicateWorkspaceError):
        service.create_workspace(user_id, "Test")


def test_workspace_duplicate_case_insensitive():
    service = WorkspaceService(MagicMock())
    user_id = uuid4()
    seen = {}

    def fake_lookup(uid, name):
        return seen.get((uid, name.lower()))

    service.workspace_repository.get_by_user_id_and_name = MagicMock(
        side_effect=fake_lookup,
    )
    service.workspace_repository.create = MagicMock(
        side_effect=lambda ws: ws,
    )
    service.db.commit = MagicMock()

    created = service.create_workspace(user_id, "Test")
    seen[(user_id, "test")] = created

    with pytest.raises(DuplicateWorkspaceError):
        service.create_workspace(user_id, "TEST")

    with pytest.raises(DuplicateWorkspaceError):
        service.create_workspace(user_id, "test")


def test_workspace_integrity_error_maps_to_duplicate():
    from sqlalchemy.exc import IntegrityError

    service = WorkspaceService(MagicMock())
    service.workspace_repository.get_by_user_id_and_name = MagicMock(
        return_value=None,
    )
    service.workspace_repository.create = MagicMock(
        side_effect=IntegrityError("stmt", "params", Exception("dup")),
    )

    with pytest.raises(DuplicateWorkspaceError):
        service.create_workspace(uuid4(), "Test")


def test_upload_triple_match_is_duplicate():
    existing = {
        upload_file_key("spec.pdf", ".pdf", 1234),
    }

    assert (
        find_duplicate_upload(
            [upload_file_key("spec.pdf", ".pdf", 1234)],
            existing,
        )
        == ("spec.pdf", ".pdf", 1234)
    )


def test_upload_same_name_different_size_allowed():
    existing = {
        upload_file_key("spec.pdf", ".pdf", 1234),
    }

    assert (
        find_duplicate_upload(
            [upload_file_key("spec.pdf", ".pdf", 9999)],
            existing,
        )
        is None
    )


def test_upload_same_name_different_extension_allowed():
    existing = {
        upload_file_key("spec.pdf", ".pdf", 1234),
    }

    assert (
        find_duplicate_upload(
            [upload_file_key("spec.pdf", ".txt", 1234)],
            existing,
        )
        is None
    )


def test_upload_case_variants_are_different_files():
    existing = {
        upload_file_key("spec.pdf", ".pdf", 1234),
    }

    assert (
        find_duplicate_upload(
            [upload_file_key("Spec.pdf", ".pdf", 1234)],
            existing,
        )
        is None
    )


def test_upload_intra_batch_duplicate_blocked():
    key = upload_file_key("a.txt", ".txt", 10)

    assert find_duplicate_upload([key, key], set()) == key


def test_upload_no_duplicates_passes():
    existing = {
        upload_file_key("old.pdf", ".pdf", 100),
    }
    incoming = [
        upload_file_key("new.pdf", ".pdf", 100),
        upload_file_key("notes.txt", ".txt", 50),
    ]

    assert find_duplicate_upload(incoming, existing) is None


def test_stored_document_key_reads_metadata():
    assert stored_document_key(
        {"file_name": "a.pdf", "extension": ".pdf", "size_bytes": 7}
    ) == ("a.pdf", ".pdf", 7)


def test_stored_document_key_missing_metadata():
    assert stored_document_key(None) == (None, None, None)
    assert stored_document_key({}) == (None, None, None)
