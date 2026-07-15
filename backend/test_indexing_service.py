from pprint import pprint
from retrieval.retriever import Retriever
from services.indexing_service import IndexingService

service = IndexingService()

service.index("../datasets/sample.txt")

retriever = Retriever()
chunks = retriever.retrieve(
    "upload project documents"
)

pprint(chunks)
