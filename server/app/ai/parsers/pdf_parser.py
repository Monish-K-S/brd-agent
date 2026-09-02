from pathlib import Path

import pymupdf

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.base import BaseParser


class PdfParser(BaseParser):
    """
    Parser for PDF files.
    """

    def parse(
        self,
        source: str,
    ) -> list[StandardDocument]:
        file_path = Path(source)

        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {source}"
            )

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(
                "Expected a .pdf file"
            )

        pdf_document = pymupdf.open(file_path)

        try:
            pages = []

            for page in pdf_document:
                text = page.get_text()

                if text.strip():
                    pages.append(text)

            content = "\n\n".join(pages)

            return [
                StandardDocument(
                    source_type="pdf",
                    title=file_path.name,
                    content=content,
                    metadata={
                        "file_name": file_path.name,
                        "extension": file_path.suffix.lower(),
                        "size_bytes": file_path.stat().st_size,
                        "page_count": len(pdf_document),
                    },
                )
            ]

        finally:
            pdf_document.close()
