"""End-to-end parser checks over the checked-in sample datasets."""

from pathlib import Path

from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.pdf_parser import PdfParser
from app.ai.parsers.txt_parser import TxtParser

# Datasets live at the repo root (server/../datasets), resolved from this
# file so the tests pass regardless of the invoking cwd.
DATASETS = Path(__file__).resolve().parent.parent.parent / "datasets"


def test_txt_parser_extracts_content():
    documents = TxtParser().parse(
        str(DATASETS / "sample_project" / "sample.txt")
    )

    assert len(documents) >= 1
    assert all(document.content.strip() for document in documents)


def test_pdf_parser_extracts_content():
    documents = PdfParser().parse(str(DATASETS / "sample2.pdf"))

    assert len(documents) >= 1
    assert all(document.content.strip() for document in documents)


def test_docx_parser_extracts_content():
    documents = DocxParser().parse(str(DATASETS / "sample3.docx"))

    assert len(documents) >= 1
    assert all(document.content.strip() for document in documents)
