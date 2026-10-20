"""Consolidation dedup (P-10).

A workspace built from several documents states the same requirement once
per document. Measured on a real 9-document workspace: **147 items of
which only 70 were distinct** — 52% byte-identical repeats. ``extend``
handed all of them to Gemini, which then spent hidden thinking tokens
working out which were "genuinely duplicated" versus merely similar.

``KnowledgeConsolidator`` now drops *identical* repeats and keeps
everything else. The line is deliberately exactly there:

- identical modulo case/whitespace  -> removed (mechanical)
- differs by a number, word, or field -> kept (semantic judgement, left
  to the BRD generation step)

These tests pin both sides of that line. If dedup ever gets hungrier, the
"near-duplicate" tests fail first.
"""

import pytest

from app.ai.consolidators.knowledge_consolidator import (
    KnowledgeConsolidator,
)
from app.ai.models.knowledge.assumption import Assumption
from app.ai.models.knowledge.document_knowledge import (
    DocumentKnowledge,
)
from app.ai.models.knowledge.functional_requirement import (
    FunctionalRequirement,
)
from app.ai.models.knowledge.non_functional_requirement import (
    NonFunctionalRequirement,
)
from app.ai.models.knowledge.open_question import OpenQuestion
from app.ai.models.knowledge.project_metadata import ProjectMetadata
from app.ai.models.knowledge.stakeholder import Stakeholder


def _fr(description: str) -> FunctionalRequirement:
    return FunctionalRequirement(description=description)


def _consolidate(*documents: DocumentKnowledge):
    return KnowledgeConsolidator().consolidate(list(documents))


# ------------------------------------------------- exact duplicates


def test_single_document_drops_repeated_requirements():
    document = DocumentKnowledge(
        functional_requirements=[
            _fr("Users shall be able to log in."),
            _fr("Users shall be able to log in."),
            _fr("Users shall be able to log in."),
            _fr("Users shall be able to log out."),
        ],
    )

    result = _consolidate(document)

    assert [r.description for r in result.functional_requirements] == [
        "Users shall be able to log in.",
        "Users shall be able to log out.",
    ]


def test_cross_document_duplicates_collapse_to_one():
    requirement = _fr("Users shall be able to log in.")
    documents = [
        DocumentKnowledge(functional_requirements=[requirement]),
        DocumentKnowledge(functional_requirements=[requirement]),
        DocumentKnowledge(functional_requirements=[requirement]),
    ]

    result = _consolidate(*documents)

    assert len(result.functional_requirements) == 1


def test_dedup_applies_to_every_list_field():
    document = DocumentKnowledge(
        stakeholders=[
            Stakeholder(name="Maya Chen", role="PM"),
            Stakeholder(name="Maya Chen", role="PM"),
        ],
        assumptions=[Assumption("SSO is available"), Assumption("SSO is available")],
        open_questions=[
            OpenQuestion("Which region launches first?"),
            OpenQuestion("Which region launches first?"),
        ],
    )

    result = _consolidate(document)

    assert len(result.stakeholders) == 1
    assert len(result.assumptions) == 1
    assert len(result.open_questions) == 1


def test_first_seen_order_is_preserved():
    document = DocumentKnowledge(
        functional_requirements=[
            _fr("A"),
            _fr("B"),
            _fr("A"),
            _fr("C"),
            _fr("B"),
        ],
    )

    result = _consolidate(document)

    assert [r.description for r in result.functional_requirements] == [
        "A",
        "B",
        "C",
    ]


def test_case_and_whitespace_variants_are_the_same_requirement():
    document = DocumentKnowledge(
        functional_requirements=[
            _fr("Users shall be able to log in."),
            _fr("users  shall be able to\nLog in."),
        ],
    )

    result = _consolidate(document)

    assert len(result.functional_requirements) == 1


# ------------------------------------------------- must NOT merge


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # a changed threshold is a different requirement
        (
            "Sessions expire after 3.5 seconds.",
            "Sessions expire after 35 seconds.",
        ),
        # a changed actor is a different requirement
        (
            "Admins can delete users.",
            "Managers can delete users.",
        ),
        # a changed scope qualifier is a different requirement
        (
            "Users can export reports in CSV.",
            "Users can export reports in CSV and PDF.",
        ),
    ],
)
def test_near_duplicates_are_kept(first, second):
    document = DocumentKnowledge(
        functional_requirements=[_fr(first), _fr(second)],
    )

    result = _consolidate(document)

    assert [r.description for r in result.functional_requirements] == [
        first,
        second,
    ]


def test_structured_items_differing_in_one_field_are_kept():
    document = DocumentKnowledge(
        non_functional_requirements=[
            NonFunctionalRequirement(
                category="performance",
                description="Respond within 200 ms.",
            ),
            NonFunctionalRequirement(
                category="availability",
                description="Respond within 200 ms.",
            ),
        ],
    )

    result = _consolidate(document)

    assert len(result.non_functional_requirements) == 2


def test_none_field_does_not_collide_with_a_populated_one():
    document = DocumentKnowledge(
        stakeholders=[
            Stakeholder(name="Maya Chen", role=None),
            Stakeholder(name="Maya Chen", role="Product Manager"),
        ],
    )

    result = _consolidate(document)

    assert len(result.stakeholders) == 2


# ------------------------------------------------- unchanged behaviour


def test_empty_input_still_returns_empty_knowledge():
    result = _consolidate()

    assert result.project_metadata is None
    assert result.functional_requirements == []


def test_project_metadata_comes_from_the_first_document():
    first = ProjectMetadata(project_name="Sourcify", description="BRDs")
    documents = [
        DocumentKnowledge(project_metadata=first),
        DocumentKnowledge(
            project_metadata=ProjectMetadata(project_name="Other"),
        ),
    ]

    result = _consolidate(*documents)

    assert result.project_metadata.project_name == "Sourcify"
