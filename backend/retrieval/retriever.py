from models.document_chunk import DocumentChunk
from vectorstore.vector_store import VectorStore

class Retriever:
    """
    Retrieves the most relevant document chunks for a user query.
    """

    def __init__(self):
        self.vector_store = VectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """
        Retrieve the most relevant document chunks.
        """

        return self.vector_store.search(
            query=query,
            top_k=top_k,
        )

    def build_context(
        chunks: list[DocumentChunk],
    ) -> str:
        """
        Build an LLM-ready context string from retrieved document chunks.
        """

        sections = []

        for chunk in chunks:
            section = (
                f"Source: {chunk.source_type}\n"
                f"Chunk: {chunk.chunk_index}\n\n"
                f"{chunk.content}"
            )

            sections.add(section)

        return "\n\n" + ("=" * 50 + "\n\n").join(sections)
