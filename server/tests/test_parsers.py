from app.ai.parsers.docx_parser import DocxParser
from app.ai.parsers.pdf_parser import PdfParser
from app.ai.parsers.txt_parser import TxtParser


def main():
    sources = [
        (
            "../datasets/sample_project/sample.txt",
            TxtParser(),
        ),
        (
            "../datasets/sample2.pdf",
            PdfParser(),
        ),
        (
            "../datasets/sample3.docx",
            DocxParser(),
        ),
    ]

    for source, parser in sources:
        documents = parser.parse(source)

        print(f"\nSource: {source}")
        print(f"Parser: {parser.__class__.__name__}")

        for document in documents:
            print(document)


if __name__ == "__main__":
    main()
