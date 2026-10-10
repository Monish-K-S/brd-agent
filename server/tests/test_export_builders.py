"""Export builder regressions.

Covers the real 2026-09-18 crash: non-latin-1 literals (U+2022, U+2013)
reaching fpdf2's core Helvetica raise FPDFUnicodeEncodingException, so the
PDF builder must normalize them while the DOCX builder (Arial) keeps them.
"""

import re
import zipfile
import zlib

from app.ai.builders.brd_document_builder import BRDDocumentBuilder
from app.ai.builders.brd_docx_builder import BRDDocxBuilder
from app.ai.models.artifacts.assumptions_and_constraints import (
    AssumptionsAndConstraints,
)
from app.ai.models.artifacts.brd import BRD
from app.ai.models.artifacts.business_objectives_section import (
    BusinessObjectivesSection,
)
from app.ai.models.artifacts.business_requirements import BusinessRequirements
from app.ai.models.artifacts.executive_summary import ExecutiveSummary
from app.ai.models.artifacts.functional_requirements_section import (
    FunctionalRequirementsSection,
)
from app.ai.models.artifacts.non_functional_requirements_section import (
    NonFunctionalRequirementsSection,
)
from app.ai.models.artifacts.open_questions_section import OpenQuestionsSection
from app.ai.models.artifacts.project_overview import ProjectOverview
from app.ai.models.artifacts.risks_and_decisions import RisksAndDecisions
from app.ai.models.artifacts.scope import Scope
from app.ai.models.artifacts.stakeholders_section import (
    StakeholderEntry,
    StakeholdersSection,
)

def pdf_text(path) -> str:
    """Raw bytes plus zlib-inflated stream contents (fpdf2 compresses)."""
    raw = path.read_bytes()
    parts = [raw.decode("latin-1")]
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.DOTALL):
        try:
            parts.append(zlib.decompress(match.group(1)).decode("latin-1"))
        except Exception:
            continue
    return "\n".join(parts)


LONG = (
    "The platform ingests source files uploaded between 2024–2026 — PDFs, "
    "Word documents, and Gmail threads — then drafts structured requirements "
    "for review. Authors' notes, “quoted” decisions, and follow-ups… are "
    "preserved across regeneration so reviewers see stable output. " * 6
)


def make_brd() -> BRD:
    return BRD(
        executive_summary=ExecutiveSummary(content=LONG),
        project_overview=ProjectOverview(
            project_name="Sample BRD",
            description=LONG,
        ),
        business_objectives=BusinessObjectivesSection(
            objectives=[
                "Ship the first structured draft in weeks, not months.",
                "Keep every section traceable to its source material.",
            ]
        ),
        scope=Scope(
            in_scope=["Document ingestion", "BRD generation"],
            out_of_scope=["Version history"],
        ),
        stakeholders=StakeholdersSection(
            stakeholders=[
                StakeholderEntry(
                    name="Ada Lovelace",
                    role="Product Lead",
                    organization="Analytical Engines",
                ),
            ]
        ),
        business_requirements=BusinessRequirements(
            requirements=["BR-1: Upload TXT, PDF, and DOCX sources."]
        ),
        functional_requirements=FunctionalRequirementsSection(
            requirements=["FR-1: Generate an 11-section BRD."]
        ),
        non_functional_requirements=NonFunctionalRequirementsSection(
            requirements=["NFR-1: Exports must open in standard readers."]
        ),
        assumptions_and_constraints=AssumptionsAndConstraints(
            assumptions=["Sources are in English."],
            constraints=["10MB per-file upload cap."],
        ),
        risks_and_decisions=RisksAndDecisions(
            risks=["LLM output needs human review."],
            decisions=["Google-only authentication."],
        ),
        # Empty on purpose: builders must render the "None specified" state.
        open_questions=OpenQuestionsSection(questions=[]),
    )


def test_pdf_build_survives_non_latin1_content(tmp_path):
    """Bullets (U+2022) and dashes (U+2013/U+2014) must not crash fpdf2."""
    output = tmp_path / "brd.pdf"

    BRDDocumentBuilder().build(make_brd(), str(output))

    raw = output.read_bytes()
    assert raw.startswith(b"%PDF")
    assert "None specified" in pdf_text(output)


def test_pdf_build_survives_unmapped_unicode(tmp_path):
    """Chars outside the explicit map (H-1: ->, EUR, checkmarks, CJK
    punctuation) must degrade gracefully, never 500 the PDF download."""
    output = tmp_path / "brd-hostile.pdf"

    hostile = (
        "Latency p99 must drop 20% → 100ms; cost <= EUR 500 ≥ baseline. "
        "Steps: ✓ done, ✗ pending. Risks: A⇒B, x≠y, a≈b, √n < ∞. "
        "Items ▪ alpha ◆ beta ™. Notes、first，second."
        "Unmapped emoji 🙂 and snowman ☃ degrade to '?'."
    )
    brd = make_brd()
    brd.business_requirements.requirements.append(hostile)

    BRDDocumentBuilder().build(brd, str(output))

    raw = output.read_bytes()
    assert raw.startswith(b"%PDF")
    text = pdf_text(output)
    assert "->" in text  # mapped arrow survives readably
    assert "EUR" in text  # mapped euro survives readably


def test_normalize_text_always_latin1_safe():
    """_normalize_text output must always be latin-1 encodable, no matter
    the input — the safety net, not the map, is the crash guarantee."""
    hostile = "→←↑↓⇒≥≤≠≈√∞€✓✗▪◆™、，🙂☃零"
    normalized = BRDDocumentBuilder._normalize_text(hostile)
    normalized.encode("latin-1")  # raises on any survivor
    assert "?" in normalized  # truly unmapped chars (emoji/CJK) degrade


def test_pdf_has_page_folios(tmp_path):
    output = tmp_path / "brd.pdf"

    BRDDocumentBuilder().build(make_brd(), str(output))

    text = pdf_text(output)
    assert re.search(r"/Count\s+(\d+)", text) is not None
    # Folio renders the current page number as show-text.
    assert re.search(r"\(1\)\s*Tj", text) is not None


def test_docx_build_keeps_unicode_and_justifies(tmp_path):
    output = tmp_path / "brd.docx"

    BRDDocxBuilder().build(make_brd(), str(output))

    with zipfile.ZipFile(output) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")

    assert 'w:val="both"' in xml
    assert "line=\"276\"" in xml  # 1.15 spacing
    assert "–" in xml  # en-dash survives under Arial
    assert "None specified" in xml


def test_docx_footer_has_page_field(tmp_path):
    output = tmp_path / "brd.docx"

    BRDDocxBuilder().build(make_brd(), str(output))

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert any(n.startswith("word/footer") for n in names)
        footer_xml = archive.read(
            next(n for n in names if n.startswith("word/footer"))
        ).decode("utf-8")

    assert "PAGE" in footer_xml
