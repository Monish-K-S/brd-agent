from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer


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
    generator = EmbeddingGenerator()
    embedded_chunks = generator.generate(chunks)

    print("=" * 70)
    print("EMBEDDING TEST")
    print("=" * 70)

    print(f"Total Chunks: {len(embedded_chunks)}")

    for embedded_chunk in embedded_chunks:
        print("-" * 70)
        print(f"Chunk Index : {embedded_chunk.chunk.chunk_index}")
        print(f"Source Type : {embedded_chunk.chunk.source_type}")
        print(f"Model       : {embedded_chunk.embedding_model}")

        print("\nContent:")
        print(embedded_chunk.chunk.content)

        print("\nEmbedding Dimension:")
        print(len(embedded_chunk.embedding))

        print("\nFirst 10 Values:")
        print(embedded_chunk.embedding[:10])

        print()


if __name__ == "__main__":
    main()
