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

        # Extract the text from each chunk
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings in a single batch
        embeddings = self.model.encode(texts)

        embedded_chunks: list[EmbeddedChunk] = []

        for chunk, embedding in zip(chunks, embeddings):
            embedded_chunks.append(
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=embedding.tolist(),
                    embedding_model=self.DEFAULT_MODEL,
                )
            )

        return embedded_chunks
