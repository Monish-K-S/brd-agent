"""Run one benchmark scenario through the real pipeline, without a database.

This mirrors ``DocumentExtractionService`` + ``ProjectKnowledgeService`` +
``BRDService`` step for step, minus persistence. The point is to measure
the code that ships, not a reimplementation of it — so it calls the real
parsers, the real PDF builder, the real Sarvam extractor, the real
consolidator and the real Gemini generator.

Two deliberate omissions, both documented rather than faked:

* **Aggregate truncation** (`_fit_to_aggregate_budget`) is a private
  method of a service that requires a database session. Benchmark
  fixtures are a few thousand characters against a one-million budget, so
  truncation cannot trigger; if a fixture ever grows past the budget the
  runner fails loudly instead of silently measuring a different pipeline.
* **Multi-document consolidation** is not exercised, because production
  produces one aggregate extraction row per workspace and therefore takes
  the single-document path too. Calling ``consolidate([one])`` is
  faithful, not a shortcut.
"""

import hashlib
import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.builders.project_document_builder import ProjectDocumentBuilder
from app.ai.consolidators.knowledge_consolidator import KnowledgeConsolidator
from app.ai.extractors.sarvam_extractor import SarvamExtractor
from app.ai.extractors.sarvam_knowledge_mapper import SarvamKnowledgeMapper
from app.ai.generators.gemini_brd_generator import GeminiBRDGenerator
from app.ai.models.knowledge.project_knowledge import ProjectKnowledge
from app.core.config import settings
from app.evals.datasets import Scenario
from app.evals.metrics.coverage import score_coverage
from app.evals.metrics.duplication import score_duplication
from app.evals.metrics.groundedness import score_groundedness
from app.evals.metrics.retention import score_retention
from app.evals.metrics.structure import score_structure
from app.services.document_ingestion_service import DocumentIngestionService

AI_DIR = Path(__file__).resolve().parent.parent / "ai"
DOCUMENT_KNOWLEDGE_SCHEMA = AI_DIR / "schemas" / "document_knowledge_schema.json"
BRD_SCHEMA = AI_DIR / "schemas" / "brd_schema.json"

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent / ".cache"

MODE_LIVE = "live"
MODE_REPLAY = "replay"


class ScenarioRunError(RuntimeError):
    """A scenario could not be run (bad fixture, missing cache, bad response)."""


@dataclass
class RunConfig:
    mode: str = MODE_LIVE
    thinking_budget: int | None = None
    model: str | None = None
    dedupe: bool = True
    cache_dir: Path | None = None


@dataclass
class ScenarioResult:
    scenario: str
    mode: str
    timings: dict = field(default_factory=dict)
    usage: dict | None = None
    metrics: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    # Kept in results.json on purpose: a score you cannot inspect against
    # the document that produced it is not evidence. The document is a
    # few KB, and it is the difference between "retention was 0.86" and
    # "here is the requirement that was lost".
    brd: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "mode": self.mode,
            "timings": self.timings,
            "usage": self.usage,
            "metrics": self.metrics,
            "summary": self.summary,
            "brd": self.brd,
        }


def run_scenario(
    scenario: Scenario,
    config: RunConfig | None = None,
    extractor=None,
    generator=None,
) -> ScenarioResult:
    """Run one scenario end to end and return its measured result.

    ``extractor`` and ``generator`` are injectable so the harness itself
    can be tested without network calls. When omitted, the real ones are
    built exactly as the services build them.
    """
    config = config or RunConfig()

    result = ScenarioResult(scenario=scenario.name, mode=config.mode)

    documents = _parse(scenario, result)
    pdf_path = _build_pdf(scenario, documents, result)

    try:
        raw = _extract(scenario, pdf_path, config, result, extractor)
    finally:
        pdf_path.unlink(missing_ok=True)

    document_knowledge_raw = raw

    project_knowledge = _consolidate_project(
        document_knowledge_raw,
        dedupe=config.dedupe,
        result=result,
    )

    brd, usage = _generate(project_knowledge, config, result, generator)

    result.brd = brd if isinstance(brd, dict) else {}
    result.usage = usage

    _score(scenario, brd, project_knowledge, result)

    return result


# --------------------------------------------------------------- stages


def _parse(scenario: Scenario, result: ScenarioResult):
    ingestion = DocumentIngestionService()

    started = time.perf_counter()

    documents = []

    for path in scenario.inputs:
        documents.extend(ingestion.ingest(path))

    if not documents:
        raise ScenarioRunError(f"{scenario.name}: no documents were parsed")

    total_chars = sum(len(document.content or "") for document in documents)

    # The real pipeline truncates here. A fixture that would be truncated
    # is measuring a different pipeline, so refuse rather than guess.
    if total_chars >= settings.max_aggregate_chars:
        raise ScenarioRunError(
            f"{scenario.name}: {total_chars} chars exceeds "
            f"max_aggregate_chars ({settings.max_aggregate_chars}); "
            "the real pipeline would truncate this scenario"
        )

    result.timings["parse"] = round(time.perf_counter() - started, 3)

    return documents


def _build_pdf(scenario: Scenario, documents, result: ScenarioResult) -> Path:
    started = time.perf_counter()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        pdf_path = Path(temp_file.name)

    try:
        ProjectDocumentBuilder().build(
            documents=documents,
            output_path=str(pdf_path),
        )
    except Exception:
        pdf_path.unlink(missing_ok=True)
        raise

    result.timings["aggregate_pdf"] = round(time.perf_counter() - started, 3)

    return pdf_path


def _extract(scenario, pdf_path, config, result, extractor):
    cache_path = _cache_path(scenario, config)

    started = time.perf_counter()

    if config.mode == MODE_REPLAY:
        raw = _read_cache(cache_path, scenario)
    else:
        if extractor is None:
            extractor = SarvamExtractor(
                schema_path=DOCUMENT_KNOWLEDGE_SCHEMA,
            )

        raw = extractor.extract(
            pdf_path=pdf_path,
            output_path=cache_path,
        )

    result.timings["extraction"] = round(time.perf_counter() - started, 3)

    if not isinstance(raw, dict):
        raise ScenarioRunError(
            f"{scenario.name}: extraction returned {type(raw).__name__}, not a dict"
        )

    return raw


def _consolidate_project(raw, *, dedupe, result):
    started = time.perf_counter()

    document_knowledge = SarvamKnowledgeMapper().map(raw)

    if dedupe:
        knowledge = KnowledgeConsolidator().consolidate([document_knowledge])
    else:
        knowledge = _without_dedupe(document_knowledge)

    result.timings["consolidation"] = round(time.perf_counter() - started, 3)

    return knowledge


def _without_dedupe(document_knowledge) -> ProjectKnowledge:
    """Build ProjectKnowledge keeping duplicates, for the dedup A/B.

    Reuses the consolidator's own field list so a new field cannot be
    forgotten here; the only difference from the production path is the
    missing ``_dedupe`` call.
    """
    return ProjectKnowledge(
        project_metadata=document_knowledge.project_metadata,
        **{
            field_name: list(getattr(document_knowledge, field_name))
            for field_name in KnowledgeConsolidator._LIST_FIELDS
        },
    )


def _generate(project_knowledge, config, result, generator):
    started = time.perf_counter()

    if generator is None:
        generator = GeminiBRDGenerator(
            schema_path=BRD_SCHEMA,
            thinking_budget=config.thinking_budget,
            model=config.model,
        )

    brd = generator.generate(project_knowledge)

    result.timings["generation"] = round(time.perf_counter() - started, 3)

    usage = getattr(generator, "last_usage", None)

    return brd, usage if isinstance(usage, dict) else None


def _score(scenario, brd, project_knowledge, result: ScenarioResult) -> None:
    started = time.perf_counter()

    structure = score_structure(brd)
    retention = score_retention(project_knowledge, brd)
    groundedness = score_groundedness(brd, project_knowledge)
    duplication = score_duplication(brd)
    coverage = score_coverage(brd, scenario.expected)

    result.timings["scoring"] = round(time.perf_counter() - started, 3)

    result.metrics = {
        "structure": structure,
        "retention": retention,
        "groundedness": groundedness,
        "duplication": duplication,
        "coverage": coverage,
    }

    result.summary = {
        "valid": structure["valid"],
        "sections_present": structure["sections_present"],
        "recall": coverage["recall"],
        "facts_total": coverage["facts_total"],
        "facts_matched": coverage["facts_matched"],
        "retention": retention["overall_retention"],
        "unsupported_rate": groundedness["unsupported_rate"],
        "duplicate_items": duplication["duplicate_items"],
        "total_seconds": round(sum(result.timings.values()), 3),
    }


# ---------------------------------------------------------------- cache


def _cache_path(scenario: Scenario, config: RunConfig) -> Path:
    """One cache file per scenario *content*.

    Keyed on the input bytes, so editing a fixture invalidates its cache
    automatically — otherwise a stale extraction would be replayed
    against changed documents and the coverage score would be measuring
    the old ones.
    """
    cache_dir = config.cache_dir or DEFAULT_CACHE_DIR

    digest = hashlib.sha256()

    for path in scenario.inputs:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())

    return cache_dir / f"{scenario.name}-{digest.hexdigest()[:12]}.json"


def _read_cache(cache_path: Path, scenario: Scenario) -> dict:
    if not cache_path.is_file():
        raise ScenarioRunError(
            f"{scenario.name}: no cached extraction at {cache_path.name}. "
            f"Run once without --replay to create it."
        )

    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioRunError(
            f"{scenario.name}: cached extraction is not valid JSON ({exc})"
        ) from exc
