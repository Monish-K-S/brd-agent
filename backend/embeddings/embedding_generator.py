from models.document_chunk import DocumentChunk
from models.embedded_chunk import EmbeddedChunk
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Generates vector embeddings for DocumentChunks
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        self.model = SentenceTransformer(self.DEFAULT_MODEL)

    def generate(
        self,
        chunks: list[DocumentChunk],
    ) -> list[EmbeddedChunk]:
        """
        Convert DocumentChunk to EmbeddedChunk
        """

        return []
