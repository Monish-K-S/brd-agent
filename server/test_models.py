from sqlalchemy import inspect

from app.db.models.user import User
from app.db.models.workspace import Workspace
from app.db.models.standard_document import StandardDocument
from app.db.models.document_extraction import DocumentExtraction
from app.db.models.document_extraction_document import (
    DocumentExtractionDocument,
)
from app.db.models.project_knowledge import ProjectKnowledge
from app.db.models.brd import BRD


models = [
    User,
    Workspace,
    StandardDocument,
    DocumentExtraction,
    DocumentExtractionDocument,
    ProjectKnowledge,
    BRD,
]


def test_models_and_relationships_load():
    for model in models:
        inspect(model)
