from models.standard_document import StandardDocument
from preprocessing.document_normalizer import DocumentNormalizer


def main():
    raw_content = (
        "Project\tManager\r\n"
        "Business Analyst    \r\n"
        "\r\n"
        "\r\n"
        "\r\n"
        "Requirement 1\x00\r\n"
        "Requirement 2\x08\r\n"
        "Café\r\n"
    )

    document = StandardDocument(
        source_type="txt",
        title="normalization_test.txt",
        content=raw_content,
    )

    normalizer = DocumentNormalizer()

    normalized_documents = normalizer.normalize([document])

    normalized = normalized_documents[0]

    print("=" * 60)
    print("BEFORE")
    print("=" * 60)
    print(repr(raw_content))

    print("\n")

    print("=" * 60)
    print("AFTER")
    print("=" * 60)
    print(repr(normalized.content))

    print("\n")

    print("=" * 60)
    print("NORMALIZED CONTENT")
    print("=" * 60)
    print(normalized.content)


if __name__ == "__main__":
    main()
