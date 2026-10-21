import logging
import time
from pathlib import Path

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.parser_factory import ParserFactory
from app.ai.preprocessing.document_normalizer import DocumentNormalizer


logger = logging.getLogger("brd-agent.ingestion")


class DocumentIngestionService:
    """
    Handles ingestion of uploaded source files.

    Responsibilities:
    - Detect the appropriate parser
    - Parse the source file into StandardDocument objects
    - Normalize the parsed documents
    """

    def __init__(self):
        self.normalizer = DocumentNormalizer()

    def ingest(
        self,
        file_path: str | Path,
    ) -> list[StandardDocument]:
        """
        Parse and normalize a source file.

        Returns AI-layer StandardDocument objects.

        Timing is logged per file because this runs *inside* the upload
        request: a request may parse up to `max_upload_files` documents
        before it responds, so this is the number that explains a slow
        upload. It is also the number that decides whether background
        ingestion (P-6) is worth its API contract change — do not replace
        it with an assumption.
        """

        file_path = Path(file_path)

        started = time.perf_counter()

        parser = ParserFactory.get_parser(
            str(file_path),
        )

        documents = parser.parse(
            str(file_path),
        )

        normalized_documents = self.normalizer.normalize(
            documents,
        )

        logger.info(
            "parsed %s in %.2fs -> %s document(s), %s chars",
            file_path.suffix.lower() or "(no suffix)",
            time.perf_counter() - started,
            len(normalized_documents),
            sum(
                len(document.content or "")
                for document in normalized_documents
            ),
        )

        return normalized_documents
