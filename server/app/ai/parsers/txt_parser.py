from pathlib import Path

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.base import BaseParser


class TxtParser(BaseParser):
    """
    Parser for plain text (.txt) files.
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

        if file_path.suffix.lower() != ".txt":
            raise ValueError(
                "Expected a .txt file"
            )

        content = file_path.read_text(
            encoding="utf-8"
        )

        return [
            StandardDocument(
                source_type="txt",
                title=file_path.name,
                content=content,
                metadata={
                    "file_name": file_path.name,
                    "extension": file_path.suffix.lower(),
                    "size_bytes": file_path.stat().st_size,
                },
            )
        ]
