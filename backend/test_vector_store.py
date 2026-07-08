from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer
from vectorstore.vector_store import VectorStore


def main():
    parser = TxtParser()
    documents = parser.parse("../datasets/sample.txt")

    normalizer = DocumentNormalizer()
    documents = normalizer.normalize(documents)

    chunker = SourceAwareChunker()
    chunks = chunker.chunk(documents)

    embedding_generator = EmbeddingGenerator()
    embedded_chunks = embedding_generator.generate(chunks)

    vector_store = VectorStore()

    vector_store.add(embedded_chunks)

    # This will call your search() method
    vector_store.search("project requirements")


if __name__ == "__main__":
    main()
