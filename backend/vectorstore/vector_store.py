from pprint import pprint

import chromadb

from embeddings.embedding_generator import EmbeddingGenerator
from models.embedded_chunk import EmbeddedChunk


class VectorStore:
    """
    Stores and retrieves EmbeddedChunks using semantic similarity
    """

    COLLECTION_NAME = "brd_chunks"

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_generator = EmbeddingGenerator()

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME
        )

    def add(
        self,
        chunks: list[EmbeddedChunk],
    ) -> None:
        """
        Store embedded chunks in the vector database
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
    ) -> list[EmbeddedChunk]:
        """
        Retrieves the most semantically similar EmbddedChunks
        """
        query_embdedding = self.embedding_generator.generate_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embdedding],
            n_results=top_k,
        )
        pprint(results)
        return []
