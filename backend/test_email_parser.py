from parsers.email_parser import EmailParser


def main():
    parser = EmailParser()

    documents = parser.parse("../datasets/sample_emails/email_1.eml")

    # print(f"Parsed {len(documents)} document(s)\n") = 1

    document = documents[0]

    print("=" * 50)
    print("Source Type :", document.source_type)
    print("Title       :", document.title)
    print("Author      :", document.author)
    print("Created At  :", document.created_at)
    print("Participants:", document.participants)

    print("\nContent")
    print("-" * 50)
    print(document.content)

    print("\nMetadata")
    print("-" * 50)
    print(document.metadata)


if __name__ == "__main__":
    main()
