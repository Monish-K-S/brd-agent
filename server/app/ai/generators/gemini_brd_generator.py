import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.ai.models.knowledge.project_knowledge import (
    ProjectKnowledge,
)
from app.core.config import settings

logger = logging.getLogger("brd-agent.generation")


class GeminiBRDGenerator:
    """
    Generates a structured BRD from ProjectKnowledge using Gemini.
    """

    MODEL = "gemini-2.5-flash"

    # The SDK retries by default (5 attempts on 408/429/5xx). Set an
    # explicit, smaller budget instead: bounded worst-case latency, and
    # no compounding with a hand-rolled loop.
    RETRY_ATTEMPTS = 2
    RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

    def __init__(
        self,
        schema_path: str | Path,
        timeout_seconds: int | None = None,
        thinking_budget: int | None = None,
        model: str | None = None,
    ) -> None:
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        self.schema_path = Path(schema_path)

        # Overridable per instance so the evaluation harness can compare
        # two models on identical input. The class constant stays the
        # default, so nothing changes for the app.
        self.model = model or self.MODEL

        # Token split of the most recent call, or None before the first
        # one. Exposed so the evaluator can record usage as data instead
        # of scraping the log line.
        self.last_usage: dict | None = None

        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.gemini_timeout_seconds
        )

        # 0 = no thinking. Exposed rather than hardcoded so the budget can
        # be raised without a code change if output quality ever regresses.
        self.thinking_budget = (
            thinking_budget
            if thinking_budget is not None
            else settings.gemini_thinking_budget
        )

        self.http_options = types.HttpOptions(
            # google-genai expresses this in milliseconds.
            timeout=self.timeout_seconds * 1000,
            retry_options=types.HttpRetryOptions(
                attempts=self.RETRY_ATTEMPTS,
                initial_delay=1.0,
                max_delay=8.0,
                http_status_codes=list(self.RETRYABLE_STATUS_CODES),
            ),
        )

        self.client = genai.Client(
            api_key=api_key,
            http_options=self.http_options,
        )

    def generate(
        self,
        project_knowledge: ProjectKnowledge,
    ) -> dict:
        """
        Generate a structured BRD from ProjectKnowledge.
        """

        schema = self._load_schema()

        # A failed call must not leave the previous run's tokens behind.
        self.last_usage = None

        project_knowledge_json = json.dumps(
            project_knowledge,
            default=self._serialize_dataclass,
            indent=2,
            ensure_ascii=False,
        )

        prompt = self._build_prompt(
            project_knowledge_json,
        )

        started = time.perf_counter()

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
                "thinking_config": types.ThinkingConfig(
                    thinking_budget=self.thinking_budget,
                ),
            },
        )

        self._log_usage(
            response,
            time.perf_counter() - started,
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response"
            )

        return json.loads(response.text)

    def _log_usage(
        self,
        response,
        elapsed_seconds: float,
    ) -> None:
        """Token split for one generation call.

        ``thoughts_token_count`` is the hidden reasoning the user never
        sees but pays latency (and output-token rates) for. Without this
        line, "why is BRD generation slow" is unanswerable from logs.
        """
        usage = getattr(response, "usage_metadata", None)

        if usage is None:
            return

        self.last_usage = {
            "model": self.model,
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "thought_tokens": getattr(usage, "thoughts_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
            "seconds": round(elapsed_seconds, 3),
        }

        logger.info(
            "Gemini BRD generation in %.2fs (model=%s, prompt=%s tokens, "
            "output=%s tokens, thoughts=%s tokens, total=%s tokens)",
            elapsed_seconds,
            self.model,
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "thoughts_token_count", None),
            getattr(usage, "total_token_count", None),
        )

    def _load_schema(self) -> dict:
        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"BRD schema not found: {self.schema_path}"
            )

        return json.loads(
            self.schema_path.read_text(
                encoding="utf-8",
            )
        )

    @staticmethod
    def _serialize_dataclass(
        value,
    ):
        if hasattr(value, "__dataclass_fields__"):
            return {
                field_name: GeminiBRDGenerator._serialize_dataclass(
                    getattr(value, field_name)
                )
                for field_name in value.__dataclass_fields__
            }

        if isinstance(value, list):
            return [
                GeminiBRDGenerator._serialize_dataclass(item)
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: GeminiBRDGenerator._serialize_dataclass(item)
                for key, item in value.items()
            }

        return value

    @staticmethod
    def _build_prompt(
        project_knowledge_json: str,
    ) -> str:
        return f"""
You are a senior Business Analyst responsible for producing a
professional Business Requirements Document (BRD).

Your task is to transform the provided ProjectKnowledge into a
complete, clear, and professionally written BRD.

ProjectKnowledge is the source of truth.

<instructions>

## 1. Grounding

Use only information contained in ProjectKnowledge.

Do not use external knowledge, assumptions, industry conventions,
or your own knowledge to fill gaps.

Do not invent:
- project facts
- stakeholders
- business objectives
- requirements
- constraints
- assumptions
- risks
- decisions
- scope items
- open questions
- technical architecture
- implementation details
- timelines
- metrics
- business rules

If information is not supported by ProjectKnowledge, leave the
corresponding field empty.

## 2. Preserve information

Preserve the meaning and important details of ProjectKnowledge.

Do not remove meaningful:
- actors
- actions
- conditions
- states
- permissions
- business rules
- thresholds
- numbers
- units
- dates
- frequencies
- limits
- dependencies
- scope qualifiers
- release or phase qualifiers

You may rewrite wording to make the BRD clearer, more concise,
consistent, and professional.

Rewriting must not change the meaning.

## 3. Requirement preservation

The BRD must not contain any functional requirement, scope item,
business requirement, stakeholder, decision, risk, assumption,
constraint, or other factual claim that cannot be traced back to
ProjectKnowledge.

Do not add information merely because it is plausible, typical,
logically implied, or useful for a BRD.

When synthesizing business requirements or scope, every resulting
statement must be directly supported by one or more specific pieces
of ProjectKnowledge.

Every non-functional requirement in ProjectKnowledge must be
represented in the BRD's non-functional requirements.

Do not merge separate requirements merely because they relate to
the same feature.

Do not remove a requirement because it appears similar to another.

Do not weaken a requirement by removing its conditions, limits,
actors, or qualifiers.

## 4. Business requirement synthesis

Business requirements may be synthesized from the business objectives
and relevant project knowledge.

A business requirement should describe what the business needs to
achieve or what business capability is required.

Do not turn technical implementation details into business requirements.

Do not invent business goals that are not supported by ProjectKnowledge.

## 5. Executive summary

Write a concise professional executive summary based only on
ProjectKnowledge.

The summary should communicate:
- what the project is
- why it exists
- the primary business goals
- the major scope or capability areas

Do not introduce new information.

## 6. Project overview

Use the project name and description from ProjectKnowledge.

You may improve wording for clarity, but do not change the project's
meaning.

## 7. Business objectives

Preserve the business objectives from ProjectKnowledge.

Do not convert functional requirements into business objectives.

Do not invent measurable targets unless they are present in
ProjectKnowledge.

## 8. Scope

Construct the in-scope section from capabilities and requirements
supported by ProjectKnowledge.

Use functional requirements and explicitly stated scope information
to describe what is included.

Do not introduce capabilities that are not supported by
ProjectKnowledge.

Preserve every explicitly stated out-of-scope item.

Do not assume that something is out of scope simply because it is
not mentioned.

## 9. Stakeholders

Preserve all stakeholders from ProjectKnowledge.

Do not add stakeholders based on typical project roles.

Preserve names, roles, and organizations where provided.

If a role or organization is missing, leave it unavailable rather
than inventing it.

## 10. Functional requirements

Preserve all functional requirements from ProjectKnowledge.

Rewrite them into consistent, professional requirement language
when useful.

Preserve actors, actions, conditions, states, permissions,
business rules, timing, limits, and other qualifiers.

Do not introduce implementation details.

## 11. Non-functional requirements

Preserve all non-functional requirements from ProjectKnowledge.

Do not remove measurable values or qualifiers.

Do not convert a non-functional requirement into a functional
requirement.

## 12. Assumptions and constraints

Preserve assumptions and constraints separately.

Do not convert an assumption into a fact.

Do not convert a risk or open question into a constraint.

Do not invent assumptions or constraints.

## 13. Risks and decisions

Preserve all explicitly identified risks and decisions.

Do not convert open questions, suggestions, or possible options
into decisions.

Do not invent risks merely because something could theoretically
go wrong.

## 14. Open questions

Preserve all open questions from ProjectKnowledge.

Do not answer them.

Do not convert them into requirements, decisions, assumptions,
or constraints.

## 15. Empty information

If a section has no supported information, return an empty array
or empty value according to the schema.

Never fill an empty section with generic or assumed content.

## 16. Consistency

Ensure the generated BRD is internally consistent.

For example:
- an explicitly out-of-scope item must not appear in in-scope;
- a decision must not be presented as an open question;
- an open question must not be presented as a confirmed requirement;
- a functional requirement must not contradict ProjectKnowledge.

## 17. Final validation

Before producing the response, verify that:
1. Every ProjectKnowledge field has been considered.
2. No meaningful requirement has been lost.
3. No unsupported information has been added.
4. Functional and non-functional requirements remain distinct.
5. Explicit scope exclusions are preserved.
6. Decisions, risks, assumptions, constraints, and open questions
   remain correctly classified.
7. The output conforms exactly to the provided JSON schema.

</instructions>

<project_knowledge>
{project_knowledge_json}
</project_knowledge>

<task>
Generate the complete Business Requirements Document from the
ProjectKnowledge.

Return only the structured JSON required by the schema.
</task>
"""
