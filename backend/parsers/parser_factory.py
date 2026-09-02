from pathlib import Path

from parsers.base import BaseParser
from parsers.docx_parser import DocxParser
from parsers.pdf_parser import PdfParser
from parsers.txt_parser import TxtParser


PARSERS: dict[str, type[BaseParser]] = {
    ".txt": TxtParser,
    ".pdf": PdfParser,
    ".docx": DocxParser,
}


def get_parser(source: str) -> BaseParser:
    extension = Path(source).suffix.lower()

    parser_class = PARSERS.get(extension)

    if parser_class is None:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    return parser_class()
