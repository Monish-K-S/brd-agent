from dataclasses import dataclass

from models.document_chunk import DocumentChunk


@dataclass
class EmbeddedChunk:
    """
    Represent a DocumentChunk together with its embedding
    """

    chunk: DocumentChunk

    embedding: list[float]

    embedding_model: str
