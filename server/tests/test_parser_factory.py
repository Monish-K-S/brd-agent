from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.parser_factory import ParserFactory
from app.ai.parsers.pdf_parser import PdfParser
from app.ai.parsers.txt_parser import TxtParser


def test_get_parser_returns_expected_parser():
    assert isinstance(
        ParserFactory.get_parser("sample.txt"),
        TxtParser,
    )
    assert isinstance(
        ParserFactory.get_parser("sample.pdf"),
        PdfParser,
    )
    assert isinstance(
        ParserFactory.get_parser("sample.docx"),
        DocxParser,
    )


def test_is_supported_matches_known_extensions():
    assert ParserFactory.is_supported("sample.txt")
    assert ParserFactory.is_supported("sample.pdf")
    assert ParserFactory.is_supported("sample.docx")
    assert not ParserFactory.is_supported("sample.csv")
