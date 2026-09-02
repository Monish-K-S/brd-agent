from parsers.pdf_parser import PdfParser


def main():
    parser = PdfParser()

    documents = parser.parse("../datasets/sample2.pdf")

    print(documents)


if __name__ == "__main__":
    main()
