"""P-1 — Gemini BRD generation config.

Three things the generation call must keep doing, each of which was
measured on real data on 2026-10-20 (see ``ISSUES.md`` P-1):

- **thinking disabled by default.** ``thinking_budget=0`` on the same
  ProjectKnowledge cut the call from 17-23s to ~6s; the thinking pass was
  3,319 tokens (68% of output) and the resulting BRD was within 1% of the
  same size with all 11 sections still filled. The budget stays a setting
  so it can be raised without a code change if quality ever regresses.
- **an explicit retry + timeout.** The SDK retries 5 times by default;
  this pins it to 1 retry on 408/429/5xx, so a transient 503 no longer
  fails the job and burns one of the 5/hour generates.
- **the token split is logged**, because ``thoughts_token_count`` is the
  hidden cost that made "why is generation slow" unanswerable.

No network here: the genai client is faked.
"""

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ai.generators.gemini_brd_generator import GeminiBRDGenerator
from app.core.config import Settings, settings

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "ai"
    / "schemas"
    / "brd_schema.json"
)


class _FakeModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)

        return self.response


def _response(text='{"scope": []}', usage=True):
    usage_metadata = (
        SimpleNamespace(
            prompt_token_count=5010,
            candidates_token_count=1138,
            thoughts_token_count=0,
            total_token_count=6148,
        )
        if usage
        else None
    )

    return SimpleNamespace(
        text=text,
        usage_metadata=usage_metadata,
    )


def _install_fake_client(monkeypatch, response):
    fake = SimpleNamespace(models=_FakeModels(response))

    monkeypatch.setattr(
        "google.genai.Client",
        lambda **kwargs: fake,
    )

    return fake


def _generator(monkeypatch, **kwargs):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    return GeminiBRDGenerator(
        schema_path=SCHEMA_PATH,
        **kwargs,
    )


# ------------------------------------------------- config hygiene


def test_thinking_budget_default_is_not_disabled():
    # 0 disables reasoning entirely; the default keeps a real pass because
    # judging near-duplicate requirements is the model's job (P-10).
    assert (
        Settings.model_fields["gemini_thinking_budget"].default
        == 2048
    )


def test_generator_reads_the_setting(monkeypatch):
    _install_fake_client(monkeypatch, _response())

    generator = _generator(monkeypatch)

    assert generator.thinking_budget == settings.gemini_thinking_budget


def test_thinking_config_is_sent_with_the_configured_budget(
    monkeypatch,
):
    fake = _install_fake_client(monkeypatch, _response())

    _generator(monkeypatch).generate({"project_name": "Sourcify"})

    config = fake.models.calls[0]["config"]

    assert (
        config["thinking_config"].thinking_budget
        == settings.gemini_thinking_budget
    )
    assert config["response_mime_type"] == "application/json"
    assert config["response_json_schema"]


def test_thinking_budget_can_be_raised_without_a_code_change(
    monkeypatch,
):
    fake = _install_fake_client(monkeypatch, _response())

    _generator(monkeypatch, thinking_budget=1024).generate(
        {"project_name": "Sourcify"},
    )

    config = fake.models.calls[0]["config"]

    assert config["thinking_config"].thinking_budget == 1024


# ------------------------------------------------- retry + timeout


def test_timeout_is_sent_in_milliseconds(monkeypatch):
    _install_fake_client(monkeypatch, _response())

    generator = _generator(monkeypatch, timeout_seconds=90)

    assert generator.http_options.timeout == 90_000


def test_only_one_retry_on_transient_failures(monkeypatch):
    _install_fake_client(monkeypatch, _response())

    generator = _generator(monkeypatch)
    retry = generator.http_options.retry_options

    # The SDK defaults to 5 attempts; this is deliberately pinned to 2
    # (the original request plus one retry).
    assert retry.attempts == 2
    assert 503 in retry.http_status_codes
    assert 429 in retry.http_status_codes


def test_client_is_built_with_the_http_options(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)

        return SimpleNamespace(models=_FakeModels(_response()))

    monkeypatch.setattr("google.genai.Client", fake_client)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    generator = GeminiBRDGenerator(schema_path=SCHEMA_PATH)

    assert captured["http_options"] is generator.http_options


# ------------------------------------------------- observability


def test_token_split_is_logged(monkeypatch, caplog):
    _install_fake_client(monkeypatch, _response())

    with caplog.at_level(
        logging.INFO,
        logger="brd-agent.generation",
    ):
        _generator(monkeypatch).generate({"project_name": "Sourcify"})

    assert "Gemini BRD generation in" in caplog.text
    assert "thoughts=0 tokens" in caplog.text
    assert "output=1138 tokens" in caplog.text
    assert "prompt=5010 tokens" in caplog.text


def test_missing_usage_metadata_does_not_break_generation(
    monkeypatch,
):
    _install_fake_client(monkeypatch, _response(usage=False))

    result = _generator(monkeypatch).generate(
        {"project_name": "Sourcify"},
    )

    assert result == {"scope": []}


# ------------------------------------------------- failure modes


def test_empty_response_still_raises(monkeypatch):
    _install_fake_client(monkeypatch, _response(text=""))

    with pytest.raises(RuntimeError, match="empty response"):
        _generator(monkeypatch).generate({"project_name": "Sourcify"})


# ------------------------------------------------------- evaluator hooks


def test_last_usage_is_none_before_the_first_call(monkeypatch):
    _install_fake_client(monkeypatch, _response())

    assert _generator(monkeypatch).last_usage is None


def test_last_usage_records_the_token_split(monkeypatch):
    # The evaluator reads tokens as data; scraping the log line would
    # couple it to a log format nobody promised to keep.
    _install_fake_client(monkeypatch, _response())

    generator = _generator(monkeypatch)
    generator.generate({"project_name": "Sourcify"})

    assert generator.last_usage["prompt_tokens"] == 5010
    assert generator.last_usage["output_tokens"] == 1138
    assert generator.last_usage["thought_tokens"] == 0
    assert generator.last_usage["total_tokens"] == 6148
    assert generator.last_usage["model"] == "gemini-2.5-flash"


def test_model_can_be_overridden_for_an_a_b(monkeypatch):
    fake = _install_fake_client(monkeypatch, _response())

    generator = _generator(monkeypatch, model="gemini-2.5-pro")
    generator.generate({"project_name": "Sourcify"})

    assert generator.model == "gemini-2.5-pro"
    assert fake.models.calls[0]["model"] == "gemini-2.5-pro"
    assert generator.last_usage["model"] == "gemini-2.5-pro"
