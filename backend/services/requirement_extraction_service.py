import json

from llm.gemini_client import GeminiClient
from llm.prompts import REQUIREMENT_EXTRACTION_PROMPT
from llm.response_parser import ResponseParser
from models.requirement_extraction_result import RequirementExtractionResult
from retrieval.retriever import Retriever


class RequirementExtractionService:
    """
    Orchestrates the complete requirement pipeline
    """

    def __init__(self):
        self.retriever = Retriever()
        self.gemini_client = GeminiClient()
        self.response_parser = ResponseParser()


    def extract(
        self,
        query: str,
        top_k: int = 5,
    ) -> RequirementExtractionResult:
        """
        Extract business requirements for a user query.
        """

        #Step 1
        chunks = self.retriever.retrieve(
            query=query,
            top_k=top_k,
        )

        #Step 2
        context = self.retriever.build_context(chunks)

        #Step 3
        prompt = REQUIREMENT_EXTRACTION_PROMPT.format(
            context=context,
        )

        #Step 4
        response = self.gemini_client.generate(prompt)

        #Step 5
        response_json = json.loads(response)

        #Step 6
        source_chunk_ids = [
            chunk.id
            for chunk in chunks
        ]

        #Step 7
        return self.response_parser.parse(
            response=response_json,
            source_chunk_ids=source_chunk_ids
        )
