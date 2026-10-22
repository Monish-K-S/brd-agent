"""Phase 0 — evaluation metrics.

These are the checks the evaluator will run, tested in isolation: no DB,
no network, no FastAPI. Each metric is pinned on both sides of its line —
the finding it must produce, and the false positive it must not produce.

The drift guard at the bottom matters more than it looks: the BRD list
fields are defined twice (schema and evaluator), and a new section added
to one without the other would make every item in it invisible to the
metrics without any test failing.
"""

from app.ai.models.knowledge.functional_requirement import (
    FunctionalRequirement,
)
from app.ai.models.knowledge.non_functional_requirement import (
    NonFunctionalRequirement,
)
from app.ai.models.knowledge.project_knowledge import ProjectKnowledge
from app.evals.metrics.duplication import score_duplication
from app.evals.metrics.groundedness import score_groundedness
from app.evals.metrics.latency import summarise_latency
from app.evals.metrics.retention import score_retention
from app.evals.metrics.structure import score_structure
from app.evals.models import BRD_LIST_FIELDS
from app.schemas.brd import _REQUIRED_BRD_LISTS


def _brd(**overrides) -> dict:
    brd = {
        "executive_summary": {
            "content": "This document describes the checkout redesign.",
        },
        "project_overview": {
            "project_name": "Checkout Redesign",
            "description": "A redesign of the storefront checkout flow.",
        },
        "business_objectives": {
            "objectives": ["Reduce cart abandonment by fifteen percent."],
        },
        "scope": {
            "in_scope": ["Card and wallet payments."],
            "out_of_scope": ["Cryptocurrency payments."],
        },
        "stakeholders": {
            "stakeholders": [
                {"name": "Priya Raman", "role": "Product Manager"},
            ],
        },
        "business_requirements": {
            "requirements": ["The storefront must accept card payments."],
        },
        "functional_requirements": {
            "requirements": [
                "Users must sign in with Google single sign-on.",
            ],
        },
        "non_functional_requirements": {
            "requirements": [
                "The checkout page must load in under two seconds.",
            ],
        },
        "assumptions_and_constraints": {
            "assumptions": ["The payment provider contract is renewed."],
            "constraints": ["Launch is limited to India."],
        },
        "risks_and_decisions": {
            "risks": ["A payment provider outage blocks checkout."],
            "decisions": ["Use the existing payment provider."],
        },
        "open_questions": {
            "questions": ["Should wallets ship in phase one?"],
        },
    }

    brd.update(overrides)

    return brd


# ------------------------------------------------------------- structure


def test_valid_brd_scores_every_section():
    result = score_structure(_brd())

    assert result["valid"] is True
    assert result["error"] is None
    assert result["sections_present"] == 11
    assert result["sections_expected"] == 11
    assert result["empty_sections"] == []
    assert result["item_counts"]["functional_requirements"] == 1


def test_missing_section_is_invalid_but_counts_survive():
    brd = _brd()
    del brd["open_questions"]

    result = score_structure(brd)

    assert result["valid"] is False
    assert "Missing BRD sections" in result["error"]

    # The point of scoring before validating: when half the document is
    # missing, "which half is present" is the useful part.
    assert result["item_counts"]["functional_requirements"] == 1
    assert result["sections_present"] == 10


def test_empty_section_is_reported_separately():
    result = score_structure(
        _brd(open_questions={"questions": []}),
    )

    # An empty list is schema-valid — the document is complete but thin,
    # which is a different finding from "a section is missing".
    assert result["valid"] is True
    assert result["empty_sections"] == ["open_questions"]


def test_non_dict_brd_does_not_raise():
    result = score_structure("not a brd")

    assert result["valid"] is False
    assert result["sections_present"] == 0


# ------------------------------------------------------------- retention


def _knowledge(functional=(), non_functional=()) -> ProjectKnowledge:
    return ProjectKnowledge(
        functional_requirements=[
            FunctionalRequirement(description=text)
            for text in functional
        ],
        non_functional_requirements=[
            NonFunctionalRequirement(category=category, description=text)
            for category, text in non_functional
        ],
    )


def test_verbatim_requirement_is_retained():
    text = "Users must sign in with Google single sign-on."

    result = score_retention(
        _knowledge(functional=[text]),
        _brd(functional_requirements={"requirements": [text]}),
    )

    assert result["functional"]["retention"] == 1.0
    assert result["functional"]["dropped"] == []


def test_paraphrased_requirement_is_retained():
    # The prompt explicitly allows rewording, so matching on string
    # equality would report every legitimate rephrase as a loss.
    result = score_retention(
        _knowledge(
            functional=["Users must sign in with Google single sign-on."],
        ),
        _brd(
            functional_requirements={
                "requirements": [
                    "Users authenticate through Google single sign-on.",
                ],
            },
        ),
    )

    assert result["functional"]["retention"] == 1.0


def test_dropped_requirement_reports_its_best_match():
    result = score_retention(
        _knowledge(
            functional=[
                "Users must sign in with Google single sign-on.",
                "The cart must display the running item total.",
            ],
        ),
        _brd(
            functional_requirements={
                "requirements": [
                    "Users must sign in with Google single sign-on.",
                ],
            },
        ),
    )

    functional = result["functional"]

    assert functional["input"] == 2
    assert functional["retained"] == 1
    assert functional["retention"] == 0.5

    dropped = functional["dropped"]

    assert len(dropped) == 1
    assert "running item total" in dropped[0]["text"]
    # Explainable, not just a count.
    assert dropped[0]["score"] < 0.6
    assert dropped[0]["missing_terms"]


def test_formal_rewording_with_inflections_is_retained():
    # Real false positive: the model turned "is converted into a ticket"
    # into "shall automatically convert emails ... into new tickets", and
    # surface-form matching scored it 0.5 — reporting a plainly retained
    # requirement as lost.
    result = score_retention(
        _knowledge(
            functional=[
                "Email to support is converted into a ticket automatically.",
            ],
        ),
        _brd(
            functional_requirements={
                "requirements": [
                    "The system shall automatically convert emails sent to "
                    "the support address into new tickets.",
                ],
            },
        ),
    )

    assert result["functional"]["retention"] == 1.0


def test_requirement_split_across_two_lines_is_retained():
    result = score_retention(
        _knowledge(
            functional=[
                "Priority is set by the requester and confirmed by the first responder.",
            ],
        ),
        _brd(
            functional_requirements={
                "requirements": [
                    "The system shall allow the requester to set the priority.",
                    "The first responder shall confirm the priority of a ticket.",
                ],
            },
        ),
    )

    assert result["functional"]["retention"] == 1.0


def test_retention_without_knowledge_is_unavailable():
    result = score_retention(None, _brd())

    assert result["available"] is False
    assert result["overall_retention"] is None


def test_no_extracted_requirements_is_not_perfect_retention():
    # "Nothing to check" must not read as 1.0, or an input problem would
    # look like a flawless generation.
    result = score_retention(_knowledge(), _brd())

    assert result["functional"]["retention"] is None
    assert result["overall_retention"] is None


def test_non_functional_requirements_are_scored_too():
    result = score_retention(
        _knowledge(
            non_functional=[
                ("Performance", "The checkout page must load in under two seconds."),
            ],
        ),
        _brd(),
    )

    assert result["non_functional"]["input"] == 1
    assert result["non_functional"]["retention"] == 1.0


def test_requirement_moved_to_another_section_is_still_retained():
    # The prompt asks that a requirement stay represented, not that it
    # land in a particular section. Scoping the match to one section
    # reported legitimate re-homing as a loss on real data.
    result = score_retention(
        _knowledge(
            functional=["Users must sign in with Google single sign-on."],
        ),
        _brd(
            functional_requirements={"requirements": []},
            business_requirements={
                "requirements": [
                    "Users must sign in with Google single sign-on.",
                ],
            },
        ),
    )

    assert result["functional"]["retention"] == 1.0


def test_requirement_only_mentioned_as_a_risk_is_not_retained():
    # The other side of that line: a passing mention outside the
    # requirement sections is not retention.
    result = score_retention(
        _knowledge(
            functional=[
                "Users must sign in with Google single sign-on.",
            ],
        ),
        _brd(
            functional_requirements={"requirements": []},
            business_requirements={"requirements": []},
            risks_and_decisions={
                "risks": ["Single sign-on may be unavailable."],
                "decisions": [],
            },
        ),
    )

    assert result["functional"]["retention"] == 0.0


# ----------------------------------------------------------- groundedness


def test_invented_item_is_flagged_and_restated_item_is_not():
    brd = {
        "functional_requirements": {
            "requirements": [
                "Users must sign in with Google single sign-on.",
                "The system must support biometric fingerprint login for administrators.",
            ],
        },
    }

    knowledge = _knowledge(
        functional=["Users must sign in with Google single sign-on."],
    )

    result = score_groundedness(brd, knowledge)

    assert result["available"] is True
    assert result["method"] == "lexical-overlap"
    assert result["items_scored"] == 2
    assert result["supported"] == 1
    assert result["unsupported_rate"] == 0.5

    flagged = [item["text"] for item in result["unsupported"]]

    assert len(flagged) == 1
    assert "biometric fingerprint" in flagged[0]


def test_groundedness_without_knowledge_is_unavailable():
    result = score_groundedness(_brd(), None)

    assert result["available"] is False
    assert result["unsupported_rate"] is None


def test_stakeholder_objects_are_scored_not_skipped():
    # Stakeholders are the only section holding objects, and flattening
    # them is what keeps them visible to every metric.
    knowledge = ProjectKnowledge()

    result = score_groundedness(_brd(), knowledge)

    flagged = {
        item["section"] for item in result["unsupported"]
    }

    assert "stakeholders" in flagged


# ------------------------------------------------------------ duplication


def test_exact_repeat_is_counted():
    text = "Users must sign in with Google single sign-on."

    result = score_duplication(
        _brd(
            functional_requirements={"requirements": [text, text]},
            business_requirements={"requirements": [text.upper()]},
        ),
    )

    assert result["duplicate_items"] == 2
    assert result["duplicate_groups"] == 1

    duplicate = result["duplicates"][0]

    assert duplicate["count"] == 3
    assert sorted(duplicate["sections"]) == [
        "business_requirements",
        "functional_requirements",
    ]


def test_changed_number_is_not_a_duplicate():
    # Same boundary the consolidator enforces: normalizing digits would
    # silently merge two different thresholds into one requirement.
    result = score_duplication(
        _brd(
            functional_requirements={
                "requirements": [
                    "The search must respond within 3.5 seconds.",
                    "The search must respond within 35 seconds.",
                ],
            },
        ),
    )

    assert result["duplicate_items"] == 0


def test_short_labels_are_skipped_not_reported():
    result = score_duplication(
        _brd(
            assumptions_and_constraints={
                "assumptions": ["N/A", "N/A"],
                "constraints": ["Launch is limited to India."],
            },
        ),
    )

    assert result["duplicate_items"] == 0
    assert result["skipped_short"] == 2


# --------------------------------------------------------------- latency


def test_latency_single_row_is_flagged_as_single():
    result = summarise_latency([{"generation": 5.0}])

    assert result["generation"]["n"] == 1
    assert result["generation"]["median"] == 5.0
    assert result["total"]["median"] == 5.0


def test_latency_reports_median_across_repeats():
    result = summarise_latency(
        [
            {"extraction": 20.0, "generation": 14.0},
            {"extraction": 22.0, "generation": 12.0},
        ],
    )

    assert result["extraction"]["n"] == 2
    assert result["extraction"]["median"] == 21.0
    assert result["extraction"]["min"] == 20.0
    assert result["extraction"]["max"] == 22.0
    assert result["total"]["median"] == 34.0


def test_latency_of_nothing_is_empty_not_an_error():
    assert summarise_latency([]) == {}


# ----------------------------------------------------------- drift guard


def test_brd_list_fields_match_the_schema():
    assert {
        section: tuple(fields)
        for section, fields in _REQUIRED_BRD_LISTS.items()
    } == BRD_LIST_FIELDS
