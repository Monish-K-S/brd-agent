from chunking.source_aware_chunker import SourceAwareChunker
from parsers.email_parser import EmailParser
from parsers.transcript_parser import TranscriptParser
from parsers.txt_parser import TxtParser
from preprocessing.document_normalizer import DocumentNormalizer


def print_chunks(title, chunks):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    print(f"Total Chunks: {len(chunks)}")

    for chunk in chunks:
        print("-" * 70)
        print(f"Chunk Index : {chunk.chunk_index}")
        print(f"Source Type : {chunk.source_type}")
        print(chunk.content[:150].replace("\n", " "))
        print()


def main():
    normalizer = DocumentNormalizer()
    chunker = SourceAwareChunker()

    # ---------------- TXT ----------------

    txt_parser = TxtParser()

    txt_documents = txt_parser.parse("../datasets/sample.txt")
    txt_documents = normalizer.normalize(txt_documents)

    txt_chunks = chunker.chunk(txt_documents)

    print_chunks("TXT", txt_chunks)

    # ---------------- EMAIL ----------------

    email_parser = EmailParser()

    email_documents = email_parser.parse("../datasets/sample_emails/email_1.eml")

    email_documents = normalizer.normalize(email_documents)

    email_chunks = chunker.chunk(email_documents)

    print_chunks("EMAIL", email_chunks)

    # ---------------- TRANSCRIPT ----------------

    transcript_parser = TranscriptParser()

    transcript_documents = transcript_parser.parse("../datasets/train.csv")

    transcript_documents = normalizer.normalize(transcript_documents[:1])

    transcript_chunks = chunker.chunk(transcript_documents)

    print_chunks("TRANSCRIPT", transcript_chunks)


if __name__ == "__main__":
    main()
