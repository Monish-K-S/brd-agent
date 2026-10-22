"""Phase 2 — benchmark harness: coverage, datasets, runner, reports, CLI.

Everything here is offline. The extractor and generator are injected, so
the harness can be tested without spending a Sarvam or Gemini call — which
matters because a harness bug found after a paid run costs that run twice.
"""

import json

import pytest

from app.evals import run as cli
from app.evals.compare import compare_runs
from app.evals.datasets import (
    ScenarioError,
    list_scenarios,
    load_scenario,
)
from app.evals.metrics.coverage import score_coverage
from app.evals.report import build_run, render_html, render_markdown
from app.evals.runner import (
    MODE_REPLAY,
    RunConfig,
    ScenarioRunError,
    _cache_path,
    run_scenario,
)

# The raw shape SarvamKnowledgeMapper expects: requirement lists are
# strings, non-functional requirements are objects, and open questions
# use a ``question`` key. Getting this wrong is silent — the mapper
# defaults to "" — so the fixture mirrors the real response exactly.
RAW_EXTRACTION = {
    "result": {
        "project_metadata": {
            "project_name": "Study Room Booking",
            "description": "A booking tool for library study rooms.",
        },
        "stakeholders": [
            {"name": "Library Staff", "role": "Owner", "organization": "Library"}
        ],
        "business_objectives": [
            "Replace the whiteboard booking process.",
        ],
        "functional_requirements": [
            "Students must be able to book a study room for up to two hours at a time.",
            "A booking requires a college email address.",
            "Students should be able to filter the room list by equipment, "
            "so a group that needs a projector can see only the rooms that have one.",
            "If a group cancels a booking, the slot must become available to "
            "other students immediately.",
        ],
        "non_functional_requirements": [
            {
                "category": "Availability",
                "description": "The booking tool must be available during library hours.",
            }
        ],
        "assumptions": ["Students have a college email address."],
        "constraints": ["Only the student portal is in scope."],
        "risks": ["Whiteboard bookings may continue in parallel."],
        "decisions": ["Build inside the student portal."],
        "out_of_scope": ["Reminder emails are out of scope."],
        "open_questions": [
            "Should a student be limited to one active booking at a time?",
        ],
    }
}


def _brd(**overrides) -> dict:
    brd = {
        "executive_summary": {
            "content": "A booking tool for library study rooms.",
        },
        "project_overview": {
            "project_name": "Study Room Booking",
            "description": "A booking tool for library study rooms.",
        },
        "business_objectives": {
            "objectives": ["Replace the whiteboard booking process."],
        },
        "scope": {
            "in_scope": ["Booking study rooms from the student portal."],
            "out_of_scope": ["Reminder emails are out of scope."],
        },
        "stakeholders": {
            "stakeholders": [{"name": "Library Staff", "role": "Owner"}],
        },
        "business_requirements": {
            "requirements": ["Students book rooms through the student portal."],
        },
        "functional_requirements": {
            "requirements": [
                "The library has fourteen group study rooms available for booking.",
                "Students may book a study room for up to two hours at a time.",
                "A booking requires a college email address.",
                "Students can book up to 30 days in advance.",
                "A student may hold at most two active bookings.",
                "Students can filter the room list by equipment such as a projector.",
                "Cancelling a booking makes the slot available immediately.",
                "Library staff can block a room for maintenance, and affected "
                "bookings are cancelled.",
            ],
        },
        "non_functional_requirements": {
            "requirements": [
                "The booking tool must be available during library hours.",
            ],
        },
        "assumptions_and_constraints": {
            "assumptions": ["Students have a college email address."],
            "constraints": ["Only the student portal is in scope."],
        },
        "risks_and_decisions": {
            "risks": ["Whiteboard bookings may continue in parallel."],
            "decisions": ["Build inside the student portal."],
        },
        "open_questions": {
            "questions": ["Should a student be limited to one active booking at a time?"],
        },
    }

    brd.update(overrides)

    return brd


class _FakeExtractor:
    def __init__(self, raw=None):
        self.raw = raw or RAW_EXTRACTION
        self.calls = []

    def extract(self, pdf_path, output_path=None):
        self.calls.append({"pdf_path": pdf_path, "output_path": output_path})

        if output_path is not None:
            from pathlib import Path

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(json.dumps(self.raw), encoding="utf-8")

        return self.raw


class _FakeGenerator:
    def __init__(self, brd=None):
        self.brd = brd or _brd()
        self.last_usage = {
            "model": "gemini-2.5-flash",
            "prompt_tokens": 100,
            "output_tokens": 50,
            "thought_tokens": 10,
            "total_tokens": 160,
            "seconds": 1.0,
        }

    def generate(self, project_knowledge):
        return self.brd


def _scenario():
    return load_scenario("library-rooms")


def _config(tmp_path, **overrides):
    values = {"cache_dir": tmp_path / "cache"}
    values.update(overrides)

    return RunConfig(**values)


# ------------------------------------------------------------- coverage


def test_verbatim_facts_are_captured():
    result = score_coverage(_brd(), _scenario().expected)

    assert result["available"] is True
    assert result["recall"] == 1.0
    assert result["missed"] == []


def test_paraphrase_is_captured_through_synonyms():
    brd = _brd(
        functional_requirements={
            "requirements": [
                "Fourteen rooms are available in the library.",
                "Bookings last up to 2 hours.",
                "Students must use their student email to book.",
                "A booking window of thirty days is available ahead of the visit.",
                "No one may hold two bookings at once.",
                "The list can be filtered by projector.",
                "A cancelled slot frees up instantly.",
                "Staff may block rooms for maintenance; affected bookings are cancelled.",
            ],
        },
        business_requirements={"requirements": ["Rooms are booked from the portal."]},
    )

    result = score_coverage(brd, _scenario().expected)

    assert result["recall"] == 1.0


def test_hyphen_and_space_are_the_same_phrase():
    expected = {
        "facts": [
            {
                "id": "f1",
                "text": "Single sign-on",
                "groups": [["single sign-on"]],
            },
        ]
    }

    brd = {"executive_summary": {"content": "Login uses single sign on."}}

    assert score_coverage(brd, expected)["recall"] == 1.0


def test_missing_fact_reports_the_group_that_was_absent():
    brd = _brd(
        functional_requirements={
            "requirements": [
                "The library has fourteen group study rooms available for booking.",
                "Students may book a study room for up to two hours at a time.",
                "A booking requires a college email address.",
                "Students can book up to 30 days in advance.",
                "A student may hold at most two active bookings.",
                # Mentions filtering but loses the projector requirement,
                # so only one of s6's two groups should be reported.
                "Students can filter the room list by equipment.",
                "Cancelling a booking makes the slot available immediately.",
                "Library staff can block a room for maintenance, and affected "
                "bookings are cancelled.",
            ],
        },
    )

    result = score_coverage(brd, _scenario().expected)

    assert result["facts_total"] == 8
    assert result["facts_matched"] == 7
    assert len(result["missed"]) == 1

    missed = result["missed"][0]

    assert missed["id"] == "s6"
    # Not just "a fact was missed" — which phrase went missing.
    assert missed["missing_groups"] == [["projector"]]


def test_one_group_matching_is_not_enough():
    expected = {
        "facts": [
            {"id": "f1", "text": "Google SSO", "groups": [["google"], ["sso"]]},
        ]
    }

    brd = {"executive_summary": {"content": "Login uses Google accounts."}}

    result = score_coverage(brd, expected)

    assert result["recall"] == 0.0
    assert result["missed"][0]["missing_groups"] == [["sso"]]


def test_fact_without_phrasings_is_reported_not_counted():
    # An empty group would match every document and inflate recall, so it
    # is an authoring error rather than a pass or a fail.
    expected = {
        "facts": [
            {"id": "bad", "text": "no groups", "groups": []},
            {"id": "good", "text": "rooms", "groups": [["room"]]},
        ]
    }

    result = score_coverage({"scope": {"in_scope": ["Rooms are bookable."]}}, expected)

    assert result["facts_total"] == 1
    assert result["recall"] == 1.0
    assert result["invalid"][0]["id"] == "bad"


def test_coverage_without_facts_is_unavailable():
    assert score_coverage(_brd(), None)["available"] is False
    assert score_coverage(_brd(), {"facts": []})["recall"] is None


# ------------------------------------------------------------- datasets


def test_small_scenario_loads():
    scenario = _scenario()

    assert scenario.name == "library-rooms"
    assert scenario.level == "small"
    assert len(scenario.facts) == 8
    assert len(scenario.inputs) == 1
    assert scenario.total_chars > 0


def test_unknown_scenario_is_rejected():
    with pytest.raises(ScenarioError, match="Unknown scenario"):
        load_scenario("does-not-exist")


def test_duplicate_fact_ids_are_rejected(tmp_path):
    _write_scenario(
        tmp_path,
        "dupes",
        expected={
            "facts": [
                {"id": "f1", "text": "a", "groups": [["a"]]},
                {"id": "f1", "text": "b", "groups": [["b"]]},
            ]
        },
    )

    with pytest.raises(ScenarioError, match="duplicate fact id"):
        load_scenario("dupes", tmp_path)


def test_empty_phrasing_group_is_rejected(tmp_path):
    _write_scenario(
        tmp_path,
        "empty",
        expected={"facts": [{"id": "f1", "text": "a", "groups": [[]]}]},
    )

    with pytest.raises(ScenarioError, match="empty phrasing group"):
        load_scenario("empty", tmp_path)


def test_scenario_without_documents_is_rejected(tmp_path):
    directory = tmp_path / "nofiles"
    directory.mkdir()
    (directory / "expected.json").write_text(
        json.dumps({"facts": [{"id": "f1", "text": "a", "groups": [["a"]]}]}),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioError, match="no source documents"):
        load_scenario("nofiles", tmp_path)


def _write_scenario(base, name, expected):
    inputs = base / name / "inputs"
    inputs.mkdir(parents=True)

    (inputs / "doc.txt").write_text("Some source text.", encoding="utf-8")

    (base / name / "expected.json").write_text(
        json.dumps(expected),
        encoding="utf-8",
    )


# --------------------------------------------------------------- runner


def test_runner_records_every_stage(tmp_path):
    result = run_scenario(
        _scenario(),
        _config(tmp_path),
        extractor=_FakeExtractor(),
        generator=_FakeGenerator(),
    )

    assert set(result.timings) == {
        "parse",
        "aggregate_pdf",
        "extraction",
        "consolidation",
        "generation",
        "scoring",
    }

    assert set(result.metrics) == {
        "structure",
        "retention",
        "groundedness",
        "duplication",
        "coverage",
    }

    assert result.summary["recall"] == 1.0
    assert result.summary["valid"] is True
    assert result.usage["prompt_tokens"] == 100


def test_live_run_writes_the_cache(tmp_path):
    config = _config(tmp_path)
    extractor = _FakeExtractor()

    run_scenario(_scenario(), config, extractor=extractor, generator=_FakeGenerator())

    assert _cache_path(_scenario(), config).is_file()
    assert extractor.calls[0]["output_path"] is not None


def test_replay_reads_the_cache_without_extracting(tmp_path):
    scenario = _scenario()
    config = _config(tmp_path, mode=MODE_REPLAY)

    cache = _cache_path(scenario, config)
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps(RAW_EXTRACTION), encoding="utf-8")

    extractor = _FakeExtractor()

    result = run_scenario(
        scenario,
        config,
        extractor=extractor,
        generator=_FakeGenerator(),
    )

    # The whole point of replay: no Sarvam call at all.
    assert extractor.calls == []
    assert result.summary["recall"] == 1.0


def test_replay_without_a_cache_fails_loudly(tmp_path):
    with pytest.raises(ScenarioRunError, match="no cached extraction"):
        run_scenario(
            _scenario(),
            _config(tmp_path, mode=MODE_REPLAY),
            extractor=_FakeExtractor(),
            generator=_FakeGenerator(),
        )


def test_dedupe_can_be_switched_off_for_the_ab(tmp_path):
    duplicated = {
        "result": {
            **RAW_EXTRACTION["result"],
            "functional_requirements": [
                "Students must be able to book a study room.",
                "Students must be able to book a study room.",
            ],
        }
    }

    extractor = _FakeExtractor(raw=duplicated)

    with_dedupe = run_scenario(
        _scenario(),
        _config(tmp_path),
        extractor=extractor,
        generator=_FakeGenerator(),
    )

    without_dedupe = run_scenario(
        _scenario(),
        _config(tmp_path, dedupe=False),
        extractor=_FakeExtractor(raw=duplicated),
        generator=_FakeGenerator(),
    )

    assert with_dedupe.metrics["retention"]["functional"]["input"] == 1
    assert without_dedupe.metrics["retention"]["functional"]["input"] == 2


# --------------------------------------------------------------- report


def _run_payload():
    return build_run(
        "20260101T000000",
        [
            {
                "scenario": "smoke",
                "mode": "live",
                "timings": {"parse": 0.1, "generation": 14.0},
                "usage": None,
                "metrics": {"coverage": {"missed": []}},
                "summary": {
                    "valid": True,
                    "recall": 1.0,
                    "retention": 0.9,
                    "unsupported_rate": 0.1,
                    "duplicate_items": 0,
                    "sections_present": 11,
                    "total_seconds": 14.1,
                },
            },
            {
                "scenario": "smoke",
                "mode": "live",
                "timings": {"parse": 0.2, "generation": 12.0},
                "usage": None,
                "metrics": {"coverage": {"missed": []}},
                "summary": {
                    "valid": True,
                    "recall": 0.5,
                    "retention": 0.8,
                    "unsupported_rate": 0.2,
                    "duplicate_items": 1,
                    "sections_present": 11,
                    "total_seconds": 12.2,
                },
            },
        ],
        mode="live",
        config={
            "model": "gemini-2.5-flash",
            "thinking_budget": 2048,
            "dedupe": True,
            "repeats": 2,
        },
    )


def test_run_medians_aggregate_repeats():
    run = _run_payload()
    scenario = run["scenarios"][0]

    assert scenario["summary_median"]["recall"] == 0.75
    assert scenario["summary_median"]["total_seconds"] == 13.15
    assert scenario["timing_median"]["generation"] == 13.0


def test_booleans_are_not_medianed():
    # A median over True/False is 0.5 and over True/True is fine, but
    # over a bool the first implementation returned null — which showed
    # up as a blank "valid" cell in a real report.
    run = _run_payload()

    assert run["scenarios"][0]["summary_median"]["valid"] is True


def test_html_is_self_contained():
    html = render_html(_run_payload())

    # No CDN, no font host, no tracker — it must open from disk offline.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html
    assert "Fact recall" in html


def test_markdown_reports_the_conditions_of_the_run():
    markdown = render_markdown(_run_payload())

    # A number means nothing without the settings that produced it.
    assert "Thinking budget" in markdown
    assert "2048" in markdown
    assert "| Fact recall | 0.75 |" in markdown


# -------------------------------------------------------------- compare


def test_compare_marks_improvements_and_regressions():
    baseline = _run_payload()
    faster = _run_payload()

    faster["scenarios"][0]["summary_median"]["total_seconds"] = 6.0
    faster["config"]["thinking_budget"] = 0

    markdown = compare_runs(baseline, faster)

    assert "BRD evaluation comparison" in markdown
    # total_seconds is lower-is-better, so 13.15 -> 6.0 is "better".
    assert "better" in markdown
    assert "thinking=0" in markdown


# ------------------------------------------------------------------ cli


def test_cli_lists_scenarios_without_running_anything(capsys):
    assert cli.main(["--list"]) == 0

    output = capsys.readouterr().out

    assert "library-rooms" in output
    assert "8 facts" in output


def test_cli_rejects_an_unknown_scenario(capsys):
    assert cli.main(["--scenario", "nope"]) == 2

    assert "Unknown scenario" in capsys.readouterr().err


def test_cli_rejects_zero_repeats(capsys):
    assert cli.main(["--scenario", "smoke", "--repeats", "0"]) == 2


def test_scenario_list_covers_three_levels():
    assert {"library-rooms", "clinic-booking", "helpdesk-migration"} <= set(
        list_scenarios()
    )
