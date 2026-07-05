import csv
from pathlib import Path

from models.standard_document import StandardDocument
from parsers.base import BaseParser


class TranscriptParser(BaseParser):
    """
    Parser for meeting transcript CSV files
    """

    def parse(self, source: str) -> list[StandardDocument]:
        file_path = Path(source)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found {source}")

        if file_path.suffix.lower() != ".csv":
            raise ValueError("Expected a .csv file")

        documents: list[StandardDocument] = []

        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                document = StandardDocument(
                    source_type="transcript",
                    content=row["dialogue"],
                    metadata={
                        "dataset_id": row["id"],
                        "reference_summary": row["summary"],
                    },
                )

                documents.append(document)

        return documents
