from pathlib import Path

from models.standard_document import StandardDocument
from parsers.base import BaseParser


class TxtParser(BaseParser):
    """
    Parse for plain text (.txt) files
    """

    def parse(self, source: str) -> list[StandardDocument]:
        """
        Parse a text file into a StandardDocument

        Args:
                    source: Path to the .txt file.

                Returns:
                    StandardDocument

        """

        file_path = Path(source)

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {source}")

        # Check file extension
        if file_path.suffix.lower() != ".txt":
            raise ValueError("Expected a .txt file")

        # Read file contents
        content = file_path.read_text(encoding="utf-8")

        # Create StandardDocument
        return [
            StandardDocument(
                source_type="txt",
                title=file_path.name,
                content=content,
                metadata={
                    "file_path": str(file_path.resolve()),
                    "extension": file_path.suffix,
                    "size_byte": file_path.stat().st_size,
                },
            )
        ]
