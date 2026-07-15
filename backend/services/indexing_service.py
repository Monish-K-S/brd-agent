from chunking.source_aware_chunker import SourceAwareChunker
from embeddings.embedding_generator import EmbeddingGenerator
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer
from vectorstore.vector_store import VectorStore

class IndexingService:
    """
    Builds the vector knowledge base from source documents.
    """


    def __init__(self):
        self.parser = TxtParser()
        self.normalizer = DocumentNormalizer()
        self.chunker = SourceAwareChunker()
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore()


    def index(
        self,
        source: str,
    ) -> None:
        """
        Parse, normalize, chunk, embed and index a TXT document.
        """

        documents = self.parser.parse(source)

        documents = self.normalizer.normalize(documents)

        chunks = self.chunker.chunk(documents)

        embedded_chunks = self.embedding_generator.generate(chunks)

        self.vector_store.add(embedded_chunks)
