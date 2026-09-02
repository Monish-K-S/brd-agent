from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.parser_factory import ParserFactory
from app.ai.parsers.pdf_parser import PdfParser
from app.ai.parsers.txt_parser import TxtParser


def main():
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

    assert ParserFactory.is_supported("sample.txt")
    assert ParserFactory.is_supported("sample.pdf")
    assert ParserFactory.is_supported("sample.docx")
    assert not ParserFactory.is_supported("sample.csv")

    print("ParserFactory tests passed.")


if __name__ == "__main__":
    main()
