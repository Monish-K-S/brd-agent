import chromadb
from uuid import UUID
from typing import cast

from embeddings.embedding_generator import EmbeddingGenerator
from models.document_chunk import DocumentChunk
from models.embedded_chunk import EmbeddedChunk


class VectorStore:
    """
    Stores and retrieves DocumentChunks using semantic similarity.
    """

    COLLECTION_NAME = "brd_chunks"

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME
        )

        self.embedding_generator = EmbeddingGenerator()

    def add(
        self,
        chunks: list[EmbeddedChunk],
    ) -> None:
        """
        Store embedded chunks in the vector database.
        """

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for embedded_chunk in chunks:
            ids.append(str(embedded_chunk.chunk.id))

            embeddings.append(embedded_chunk.embedding)

            documents.append(embedded_chunk.chunk.content)

            metadatas.append(
                {
                    "document_id": str(embedded_chunk.chunk.document_id),
                    "chunk_index": embedded_chunk.chunk.chunk_index,
                    "source_type": embedded_chunk.chunk.source_type,
                    "embedding_model": embedded_chunk.embedding_model,
                    **embedded_chunk.chunk.metadata,
                }
            )

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[DocumentChunk]:

        query_embedding = self.embedding_generator.generate_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        if (
            results["documents"] is None
            or results["metadatas"] is None
            or results["ids"] is None
        ):
            return []

        retrieved_chunks: list[DocumentChunk] = []

        for chunk_id, document, metadata in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
        ):
            retrieved_chunks.append(
                DocumentChunk(
                    id=UUID(chunk_id),
                    document_id=UUID(cast(str, metadata["document_id"])),
                    chunk_index=cast(int, metadata["chunk_index"]),
                    source_type=cast(str, metadata["source_type"]),
                    content=document,
                    metadata={
                        key: value
                        for key, value in metadata.items()
                        if key
                        not in {
                            "document_id",
                            "chunk_index",
                            "source_type",
                            "embedding_model",
                        }
                    },
                )
            )

        return retrieved_chunks
