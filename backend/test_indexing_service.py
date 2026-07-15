from pprint import pprint
from services.requirement_extraction_service import RequirementExtractionService
from services.indexing_service import IndexingService
from retrieval.retriever import Retriever

service = IndexingService()

#service.index("../datasets/sample.txt")

#service.index("../datasets/sample_emails/email_2.eml")

# service.index("../datasets/train.csv")

service.index_directory(
    "../datasets/sample_project"
)

service = RequirementExtractionService()
result = service.extract(
    query="Generate business requirements for this project."
)

pprint(result)
