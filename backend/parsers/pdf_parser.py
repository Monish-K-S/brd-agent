from pathlib import Path

import pymupdf

from models.standard_document import StandardDocument
from parsers.base import BaseParser


class PdfParser(BaseParser):
    """
    Parser for PDF files.
    """

    def parse(self, source: str) -> list[StandardDocument]:
        file_path = Path(source)

        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {source}"
            )

        if file_path.suffix.lower() != ".pdf":
            raise ValueError("Expected a .pdf file")

        pdf = pymupdf.open(file_path)

        try:
            page_count = len(pdf)

            content = "\n".join(
                page.get_text()
                for page in pdf
            ).strip()
        finally:
            pdf.close()

        return [
            StandardDocument(
                source_type="pdf",
                title=file_path.name,
                content=content,
                metadata={
                    "file_name": file_path.name,
                    "extension": file_path.suffix,
                    "size_bytes": file_path.stat().st_size,
                    "page_count": page_count,
                },
            )
        ]
