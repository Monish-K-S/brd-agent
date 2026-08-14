from models.standard_document import StandardDocument
from builders.project_document_builder import ProjectDocumentBuilder


documents = [
    StandardDocument(
        source_type="email",
        title="Customer Support Requirements",
        author="John Smith",
        content="Customers should be able to create support tickets.",
        participants=["John Smith", "Jane Doe"],
    ),
    StandardDocument(
        source_type="transcript",
        title="Project Meeting",
        content="The team discussed authentication and ticket assignment.",
    ),
]

builder = ProjectDocumentBuilder()

output = builder.build(
    documents=documents,
    output_path="output/project_document.pdf",
)

print(output)
