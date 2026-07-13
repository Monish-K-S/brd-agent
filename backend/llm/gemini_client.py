import os
from llm.prompts import REQUIREMENT_EXTRACTION_PROMPT
from dotenv import load_dotenv
from google import genai

load_dotenv()
class GeminiClient:
    """
    Client for interacting with the Gemini API
    """

    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self):
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

    def generate(
        self,
        context: str,
    ):
        """
        Extract business requirements from project context.
        """

        prompt = REQUIREMENT_EXTRACTION_PROMPT.format(
            context=context
        )
        response = self.client.models.generate_content(
            model=self.MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type":"application/json",
            },
        )
        return response.text
