from pathlib import Path

from builders.brd_document_builder import BRDDocumentBuilder
from builders.project_document_builder import ProjectDocumentBuilder
from consolidators.knowledge_consolidator import KnowledgeConsolidator
from extractors.sarvam_extractor import SarvamExtractor
from extractors.sarvam_knowledge_mapper import SarvamKnowledgeMapper
from generators.brd_generator import BRDGenerator
from generators.brd_mapper import BRDMapper
from models.artifacts.brd import BRD
from parsers.email_parser import EmailParser
from parsers.transcript_parser import TranscriptParser
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer


class BrdPipeline:
    """
    End-to-end pipeline for generating a BRD from project source files.
    """

    def __init__(
        self,
        document_knowledge_schema_path: str | Path,
        brd_schema_path: str | Path,
    ) -> None:
        self.email_parser = EmailParser()
        self.transcript_parser = TranscriptParser()
        self.txt_parser = TxtParser()

        self.normalizer = DocumentNormalizer()

        self.project_document_builder = ProjectDocumentBuilder()

        self.sarvam_extractor = SarvamExtractor(
            schema_path=document_knowledge_schema_path,
        )

        self.sarvam_mapper = SarvamKnowledgeMapper()

        self.knowledge_consolidator = KnowledgeConsolidator()

        self.brd_generator = BRDGenerator(
            schema_path=brd_schema_path,
        )

        self.brd_mapper = BRDMapper()

        self.brd_document_builder = BRDDocumentBuilder()

    def generate(
        self,
        source_directory: str | Path,
        output_pdf_path: str | Path,
    ) -> BRD:
        """
        Generate a BRD from all supported source files
        in a project directory.

        Returns the generated BRD domain object.
        """

        source_directory = Path(source_directory)

        output_pdf_path = Path(output_pdf_path)

        documents = self._parse_sources(source_directory)

        if not documents:
            raise ValueError(f"No supported source files found in {source_directory}")

        normalized_documents = self.normalizer.normalize(
            documents
        )

        combined_pdf_path = output_pdf_path.parent / "_project_input.pdf"

        self.project_document_builder.build(
            documents=normalized_documents,
            output_path=str(combined_pdf_path),
        )

        sarvam_response = self.sarvam_extractor.extract(
            pdf_path=combined_pdf_path,
            output_path=output_pdf_path.parent / "sarvam_extraction.json",
        )

        document_knowledge = self.sarvam_mapper.map(sarvam_response)

        project_knowledge = self.knowledge_consolidator.consolidate(
            [document_knowledge]
        )

        brd_json = self.brd_generator.generate(project_knowledge)

        brd = self.brd_mapper.map(brd_json)

        self.brd_document_builder.build(
            brd=brd,
            output_path=str(output_pdf_path),
        )

        return brd

    def _parse_sources(
        self,
        source_directory: Path,
    ):
        if not source_directory.exists():
            raise FileNotFoundError(f"Source directory not found: {source_directory}")

        if not source_directory.is_dir():
            raise ValueError(f"Expected a directory: {source_directory}")

        documents = []

        for path in sorted(source_directory.iterdir()):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()

            if suffix == ".eml":
                documents.extend(self.email_parser.parse(path))

            elif suffix == ".txt":
                documents.extend(self.txt_parser.parse(path))

            elif suffix == ".csv":
                documents.extend(self.transcript_parser.parse(path))

        return documents
