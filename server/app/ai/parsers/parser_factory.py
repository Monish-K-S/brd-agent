from pathlib import Path

from app.ai.parsers.base import BaseParser
from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.pdf_parser import PdfParser
from app.ai.parsers.txt_parser import TxtParser


class ParserFactory:
    """
    Returns the appropriate parser based on a file's extension.
    """

    _parsers: dict[str, type[BaseParser]] = {
        ".txt": TxtParser,
        ".pdf": PdfParser,
        ".docx": DocxParser,
    }

    @classmethod
    def get_parser(
        cls,
        source: str,
    ) -> BaseParser:
        extension = Path(source).suffix.lower()

        parser_class = cls._parsers.get(extension)

        if parser_class is None:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )

        return parser_class()

    @classmethod
    def is_supported(
        cls,
        source: str,
    ) -> bool:
        extension = Path(source).suffix.lower()

        return extension in cls._parsers
