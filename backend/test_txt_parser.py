from parsers.txt_parser import TxtParser


def main():
    parser = TxtParser()

    document = parser.parse("../datasets/sample.txt")

    print(document)


if __name__ == "__main__":
    main()
