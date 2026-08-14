from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer
from vectorstore.vector_store import VectorStore


def main():
    # Parse
    parser = TxtParser()
    documents = parser.parse("../datasets/sample.txt")

    # Normalize
    normalizer = DocumentNormalizer()
    documents = normalizer.normalize(documents)

    # Chunk
    chunker = SourceAwareChunker()
    chunks = chunker.chunk(documents)

    # Generate embeddings
    embedding_generator = EmbeddingGenerator()
    embedded_chunks = embedding_generator.generate(chunks)

    # Store in ChromaDB
    vector_store = VectorStore()
    vector_store.add(embedded_chunks)

    # Semantic search
    results = vector_store.search(
        query="upload project documents",
        top_k=3,
    )

    print("=" * 70)
    print("VECTOR SEARCH TEST")
    print("=" * 70)

    print(f"Retrieved Chunks: {len(results)}")

    for chunk in results:
        print("-" * 70)
        print(f"Chunk ID     : {chunk.id}")
        print(f"Document ID  : {chunk.document_id}")
        print(f"Chunk Index  : {chunk.chunk_index}")
        print(f"Source Type  : {chunk.source_type}")

        print("\nMetadata:")
        print(chunk.metadata)

        print("\nContent:")
        print(chunk.content)
        print()


if __name__ == "__main__":
    main()
