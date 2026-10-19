from pathlib import Path

import pymupdf

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.base import BaseParser
from app.core.config import settings


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

        if file_path.stat().st_size > settings.max_upload_bytes:
            raise ValueError(
                f"File too large: {file_path.name} "
                f"(max {settings.max_upload_bytes // (1024 * 1024)}MB)"
            )

        pdf_document = pymupdf.open(file_path)

        try:
            if len(pdf_document) > settings.max_pdf_pages:
                raise ValueError(
                    f"File content too large: {file_path.name} "
                    f"(max {settings.max_pdf_pages} pages)"
                )

            pages = []
            total_chars = 0

            for page in pdf_document:
                text = page.get_text()

                if text.strip():
                    total_chars += len(text)

                    if total_chars > settings.max_extracted_chars:
                        raise ValueError(
                            f"File content too large: {file_path.name} "
                            f"(max {settings.max_extracted_chars} characters)"
                        )

                    pages.append(text)

            content = "\n\n".join(pages)

            if not content.strip():
                raise ValueError(
                    f"No readable text found in: {file_path.name}"
                )

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
