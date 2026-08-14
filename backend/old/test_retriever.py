from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer
from retrieval.retriever import Retriever
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

    # Embed
    embedding_generator = EmbeddingGenerator()
    embedded_chunks = embedding_generator.generate(chunks)

    # Index
    vector_store = VectorStore()

    # Clear ChromaDB for testing
    vector_store.client.delete_collection(VectorStore.COLLECTION_NAME)
    vector_store = VectorStore()

    vector_store.add(embedded_chunks)

    # Retrieve
    retriever = Retriever()

    retrieved_chunks = retriever.retrieve(
        query="upload project documents",
        top_k=3,
    )

    print("=" * 70)
    print("RETRIEVER TEST")
    print("=" * 70)

    print("\nRetrieved Chunks\n")

    for chunk in retrieved_chunks:
        print("-" * 70)
        print(f"Chunk Index : {chunk.chunk_index}")
        print(f"Source Type : {chunk.source_type}")
        print(chunk.content)

    print("\n")
    print("=" * 70)
    print("LLM CONTEXT")
    print("=" * 70)

    context = retriever.build_context(retrieved_chunks)

    print(context)


if __name__ == "__main__":
    main()
