from pathlib import Path

from builders.project_document_builder import ProjectDocumentBuilder
from models.standard_document import StandardDocument
from parsers.email_parser import EmailParser
from parsers.transcript_parser import TranscriptParser
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer


SAMPLE_PROJECT_DIR = Path("../datasets/sample_project")
OUTPUT_PATH = Path("output/sample_project.pdf")


def test_sample_project_document_pipeline():
    documents: list[StandardDocument] = []

    # Parse emails
    email_parser = EmailParser()

    for email_file in sorted(SAMPLE_PROJECT_DIR.glob("*.eml")):
        documents.extend(email_parser.parse(str(email_file)))

    # Parse TXT
    txt_parser = TxtParser()

    for txt_file in sorted(SAMPLE_PROJECT_DIR.glob("*.txt")):
        documents.extend(txt_parser.parse(str(txt_file)))

    # Parse transcript
    transcript_parser = TranscriptParser()

    for csv_file in sorted(SAMPLE_PROJECT_DIR.glob("*.csv")):
        documents.extend(transcript_parser.parse(str(csv_file)))

    print(f"\nParsed documents: {len(documents)}")

    for document in documents:
        print(
            f"- {document.source_type}: "
            f"{document.title or 'Untitled'}"
        )

    # Verify ingestion
    assert documents
    assert all(
        isinstance(document, StandardDocument)
        for document in documents
    )

    # Normalize
    normalizer = DocumentNormalizer()
    normalized_documents = normalizer.normalize(documents)

    print(f"Normalized documents: {len(normalized_documents)}")

    assert normalized_documents == documents

    # Build combined PDF
    builder = ProjectDocumentBuilder()

    output = builder.build(
        documents=normalized_documents,
        output_path=str(OUTPUT_PATH),
    )

    output_file = Path(output)

    print(f"PDF created: {output_file.resolve()}")
    print(f"PDF size: {output_file.stat().st_size} bytes")

    # Verify PDF
    assert output_file.exists()
    assert output_file.is_file()
    assert output_file.stat().st_size > 0


if __name__ == "__main__":
    test_sample_project_document_pipeline()
