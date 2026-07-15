from pathlib import Path
from parsers.email_parser import EmailParser
from parsers.transcript_parser import TranscriptParser
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
        self.parsers = {
            ".txt": TxtParser(),
            ".eml": EmailParser(),
            ".csv": TranscriptParser(),
        }
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
        extension = Path(source).suffix.lower()

        parser = self.parsers.get(extension)

        if parser is None:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )

        documents = parser.parse(source)

        documents = self.normalizer.normalize(documents)

        chunks = self.chunker.chunk(documents)

        embedded_chunks = self.embedding_generator.generate(chunks)

        self.vector_store.add(embedded_chunks)


    def index_directory(
        self,
        directory: str,
    ) -> None:
        """
        Index every supported document inside a directory.
        """
        directory_path = Path(directory)

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not directory_path.is_dir():
            raise ValueError(f"Not a valid directory: {directory_path}")



        for file in directory_path.iterdir():
            if not file.is_file():
                continue
            if file.suffix.lower() not in self.parsers.keys():
                continue

            self.index(str(file))
