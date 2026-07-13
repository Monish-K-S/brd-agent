from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer
from services.requirement_extraction_service import RequirementExtractionService
from vectorstore.vector_store import VectorStore


def main():
    # Build the vector database

    parser = TxtParser()
    documents = parser.parse("../datasets/sample.txt")

    normalizer = DocumentNormalizer()
    documents = normalizer.normalize(documents)

    chunker = SourceAwareChunker()
    chunks = chunker.chunk(documents)

    embedding_generator = EmbeddingGenerator()
    embedded_chunks = embedding_generator.generate(chunks)

    vector_store = VectorStore()

    # Uncomment while testing if you want a clean database
    # vector_store.client.delete_collection(VectorStore.COLLECTION_NAME)
    # vector_store = VectorStore()

    vector_store.add(embedded_chunks)

    # End-to-end extraction

    service = RequirementExtractionService()

    result = service.extract(
        query="Generate business requirements for this project.",
        top_k=5,
    )

    print("=" * 70)
    print("REQUIREMENT EXTRACTION SERVICE TEST")
    print("=" * 70)

    print("\nFunctional Requirements\n")

    for requirement in result.functional_requirements:
        print(f"- {requirement.description}")

    print("\nNon-Functional Requirements\n")

    if not result.non_functional_requirements:
        print("None")

    for requirement in result.non_functional_requirements:
        print(f"- {requirement.description}")


if __name__ == "__main__":
    main()
