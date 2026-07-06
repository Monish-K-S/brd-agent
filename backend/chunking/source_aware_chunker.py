import re

from models.document_chunk import DocumentChunk
from models.standard_document import StandardDocument


class SourceAwareChunker:
    """
    Splits normalized StandardDocuments into DocumentChunks
    based on their source type.
    """

    def chunk(
        self,
        documents: list[StandardDocument],
    ) -> list[DocumentChunk]:
        """
        Convert StandardDocuments into DocumentChunks.
        """

        chunks: list[DocumentChunk] = []

        for document in documents:
            if document.source_type == "email":
                chunks.extend(self._chunk_email(document))

            elif document.source_type == "txt":
                chunks.extend(self._chunk_txt(document))

            elif document.source_type == "transcript":
                chunks.extend(self._chunk_transcript(document))

            else:
                raise ValueError(f"Unsupported source type: {document.source_type}")

        return chunks

    def _chunk_email(
        self,
        document: StandardDocument,
    ) -> list[DocumentChunk]:
        """
        One email becomes one chunk
        """

        return [
            self._create_chunk(
                document=document, chunk_index=0, content=document.content
            )
        ]

    def _chunk_txt(
        self,
        document: StandardDocument,
    ) -> list[DocumentChunk]:
        """
        Split a TXT document into paragraph-based chunks.
        """

        paragraphs = [
            paragraph.strip()
            for paragraph in document.content.split("\n\n")
            if paragraph.strip()
        ]

        chunks: list[DocumentChunk] = []

        for index, paragraph in enumerate(paragraphs):
            chunks.append(
                self._create_chunk(
                    document=document,
                    chunk_index=index,
                    content=paragraph,
                )
            )

        return chunks

    def _chunk_transcript(
        self,
        document: StandardDocument,
    ) -> list[DocumentChunk]:
        """
        Split a transcript into speaker-based chunks
        """

        sections = [
            section.strip()
            for section in re.split(
                r"(?=Speaker [A-Z]:)",
                document.content,
            )
            if section.strip()
        ]

        chunks: list[DocumentChunk] = []

        for index, section in enumerate(sections):
            chunks.append(
                self._create_chunk(
                    document=document,
                    chunk_index=index,
                    content=section,
                )
            )

        return chunks

    def _create_chunk(
        self,
        document: StandardDocument,
        chunk_index: int,
        content: str,
    ) -> DocumentChunk:
        """
        Create a DocumentChunk from a StandardDocument
        """

        return DocumentChunk(
            document_id=document.id,
            chunk_index=chunk_index,
            source_type=document.source_type,
            content=content,
            metadata=document.metadata.copy(),
        )
