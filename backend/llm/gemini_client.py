import os
from dotenv import load_dotenv
from google import genai

class GeminiClient:
    """
    Client for interacting with the Gemini API
    """

    MODEL_NAME = "gemini-2.5-flash"

    def __init__(
        self,
        api_key: str
    ):
        self.api_key = api_key

    def extract_requirements(
        self,
        context: str,
    ):
        """
        Extract business requirements from project context.
        """

        pass
