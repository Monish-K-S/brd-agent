import json

from models.brd import BRD
from models.requirement_extraction_result import RequirementExtractionResult
from llm.response_parser import ResponseParser
from llm.gemini_client import GeminiClient
from llm.prompts import BRD_GENERATION_PROMPT

class BRDGenerationService:
    """
    Orchestrates the complete BRD generation pipeline
    """

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.response_parser = ResponseParser()


    def generate(
        self,
        requirements: RequirementExtractionResult,
    ) -> BRD:
        """
        Generates a BRD from extracted requirements.
        """
        #Step 1
        prompt = BRD_GENERATION_PROMPT.format(
            requirements=requirements,
        )

        #Step 2
        response = self.gemini_client.generate(prompt)

        #Step 3
        response_json = json.loads(response)

        #Step 4
        return self.response_parser.parse_brd(
            response=response_json,
            requirements=requirements
        )
