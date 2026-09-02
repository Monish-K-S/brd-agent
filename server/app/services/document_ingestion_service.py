from pathlib import Path

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.parser_factory import ParserFactory
from app.ai.preprocessing.document_normalizer import DocumentNormalizer


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
        """

        file_path = Path(file_path)

        parser = ParserFactory.get_parser(
            str(file_path),
        )

        documents = parser.parse(
            str(file_path),
        )

        normalized_documents = self.normalizer.normalize(
            documents,
        )

        return normalized_documents
