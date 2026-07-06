import re
import unicodedata

from models.standard_document import StandardDocument


class DocumentNormalizer:
    """
    Performs deterministic normalization on StandardDocument objects
     without changing their business meaning.
    """

    def normalize(
        self,
        documents: list[StandardDocument],
    ) -> list[StandardDocument]:
        """
        Normalize a collection of StandardDocuments
        """

        for document in documents:
            # Normalize line endings
            document.content = document.content.replace("\r\n", "\n").replace(
                "\r", "\n"
            )
            # Normalize Unicode
            document.content = unicodedata.normalize(
                "NFC",
                document.content,
            )

            # Replace tabs with spaces

            document.content = document.content.replace("\t", " ")

            # Remove trailing whitespace
            document.content = "\n".join(
                line.rstrip() for line in document.content.split("\n")
            )

            # Remove excessive blank lines

            document.content = re.sub(
                r"\n{3,}",
                "\n\n",
                document.content,
            )

            # Remove non-printable control characters

            document.content = "".join(
                char
                for char in document.content
                if char.isprintable() or char in ("\n", "\t")
            )

        return documents
