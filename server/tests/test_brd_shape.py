"""H-2: shape validation must match what BRDMapper hard-reads.

The exact repro: PUT {"executive_summary": {}, ...} (all 11 sections
empty) used to pass validate_brd_data, persist, and then KeyError every
PDF/DOCX export until a regenerate overwrote the row.
"""

import copy
from uuid import uuid4

import pytest

from app.ai.mappers.brd_mapper import BRDMapper
from app.schemas.brd import (
    ALLOWED_BRD_SECTIONS,
    BRDDataInvalidError,
    BRDMalformedError,
    validate_brd_data,
)
from app.services.brd_service import BRDService


def make_valid_brd_data() -> dict:
    """Minimal payload carrying every key BRDMapper hard-reads."""
    return {
        "executive_summary": {"content": "Summary."},
        "project_overview": {
            "project_name": "Sample",
            "description": "Description.",
        },
        "business_objectives": {"objectives": ["Ship it."]},
        "scope": {"in_scope": ["A"], "out_of_scope": ["B"]},
        "stakeholders": {
            "stakeholders": [
                {
                    "name": "Ada",
                    "role": "Lead",
                    "organization": "Org",
                }
            ]
        },
        "business_requirements": {"requirements": ["BR-1"]},
        "functional_requirements": {"requirements": ["FR-1"]},
        "non_functional_requirements": {"requirements": ["NFR-1"]},
        "assumptions_and_constraints": {
            "assumptions": ["A"],
            "constraints": ["C"],
        },
        "risks_and_decisions": {"risks": ["R"], "decisions": ["D"]},
        "open_questions": {"questions": []},
    }


def test_all_empty_sections_rejected():
    """The H-2 repro: 11 empty objects must not validate."""
    poisoned = {section: {} for section in ALLOWED_BRD_SECTIONS}

    with pytest.raises(BRDDataInvalidError):
        validate_brd_data(poisoned)


def test_missing_section_rejected():
    data = make_valid_brd_data()
    del data["executive_summary"]

    with pytest.raises(BRDDataInvalidError, match="Missing BRD sections"):
        validate_brd_data(data)


@pytest.mark.parametrize(
    "section,field",
    [
        ("executive_summary", "content"),
        ("project_overview", "project_name"),
        ("project_overview", "description"),
    ],
)
def test_missing_hard_scalar_rejected(section, field):
    data = make_valid_brd_data()
    del data[section][field]

    with pytest.raises(BRDDataInvalidError, match=field):
        validate_brd_data(data)


def test_nameless_stakeholder_rejected():
    data = make_valid_brd_data()
    del data["stakeholders"]["stakeholders"][0]["name"]

    with pytest.raises(BRDDataInvalidError, match="name"):
        validate_brd_data(data)


def test_non_list_plural_rejected():
    data = make_valid_brd_data()
    data["business_objectives"]["objectives"] = "Ship it."

    with pytest.raises(BRDDataInvalidError, match="must be a list"):
        validate_brd_data(data)


def test_unknown_section_still_rejected():
    data = make_valid_brd_data()
    data["changelog"] = {}

    with pytest.raises(BRDDataInvalidError, match="Unknown BRD sections"):
        validate_brd_data(data)


def test_valid_payload_passes_and_maps():
    """No false rejections: whatever validates must map cleanly, so a
    legitimate client save can never wedge exports."""
    data = make_valid_brd_data()

    assert validate_brd_data(data) is None
    BRDMapper().map(copy.deepcopy(data))


class _StubWorkspace:
    name = "Sample"


class _StubWorkspaceService:
    def get_workspace_for_user(self, workspace_id, user_id):
        return _StubWorkspace()


class _StubBRDRepository:
    def __init__(self, brd_data):
        self._brd_data = brd_data

    def get_by_workspace_id(self, workspace_id):
        row = type("Row", (), {})()
        row.brd_data = self._brd_data
        return row


def _poisoned_service():
    service = BRDService.__new__(BRDService)
    service.workspace_service = _StubWorkspaceService()
    service.brd_repository = _StubBRDRepository(
        {section: {} for section in ALLOWED_BRD_SECTIONS}
    )
    service.brd_mapper = BRDMapper()
    return service


@pytest.mark.parametrize("method", ["export_brd_pdf_for_user", "export_brd_docx_for_user"])
def test_export_wraps_mapper_error(method):
    """Rows poisoned before this fix surface a 422-ready
    BRDMalformedError, never a raw KeyError 500."""
    service = _poisoned_service()

    with pytest.raises(BRDMalformedError, match="Regenerate"):
        getattr(service, method)(
            workspace_id=uuid4(),
            user_id=uuid4(),
        )
