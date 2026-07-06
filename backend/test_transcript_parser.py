from parsers.transcript_parser import TranscriptParser

parser = TranscriptParser()
documents = parser.parse("../datasets/train.csv")


print(len(documents))
# print(documents)
print(documents[0])
