from parsers.docx_parser import DocxParser


def main():
    parser = DocxParser()

    documents = parser.parse("../datasets/sample3.docx")

    print(documents)


if __name__ == "__main__":
    main()
