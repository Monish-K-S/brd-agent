from parsers.parser_factory import get_parser


def main():
    for file_path in [
        "../datasets/sample_project/sample.txt",
        "../datasets/sample2.pdf",
        "../datasets/sample3.docx",
    ]:
        parser = get_parser(file_path)

        documents = parser.parse(file_path)

        print(f"{file_path} → {parser.__class__.__name__}")
        print(documents)
        print()


if __name__ == "__main__":
    main()
