import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from models.knowledge.project_knowledge import ProjectKnowledge


class BRDGenerator:
    """
    Generates a structured BRD from ProjectKnowledge using Gemini.
    """

    MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        schema_path: str | Path,
    ) -> None:
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        self.client = genai.Client(api_key=api_key)

        self.schema_path = Path(schema_path)

    def generate(
        self,
        project_knowledge: ProjectKnowledge,
    ) -> dict:
        """
        Generate a structured BRD from ProjectKnowledge.
        """

        schema = self._load_schema()

        project_knowledge_json = json.dumps(
            project_knowledge,
            default=self._serialize_dataclass,
            indent=2,
            ensure_ascii=False,
        )

        prompt = self._build_prompt(project_knowledge_json)

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response")

        return json.loads(response.text)

    def _load_schema(self) -> dict:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"BRD schema not found: {self.schema_path}")

        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    @staticmethod
    def _serialize_dataclass(
        value,
    ):
        if hasattr(value, "__dataclass_fields__"):
            return {
                field_name: BRDGenerator._serialize_dataclass(
                    getattr(value, field_name)
                )
                for field_name in value.__dataclass_fields__
            }

        if isinstance(value, list):
            return [BRDGenerator._serialize_dataclass(item) for item in value]

        if isinstance(value, dict):
            return {
                key: BRDGenerator._serialize_dataclass(item)
                for key, item in value.items()
            }

        return value

    @staticmethod
    def _build_prompt(
        project_knowledge_json: str,
    ) -> str:
        return f"""
You are a Business Requirements Document generator.

Construct a structured Business Requirements Document
from the provided ProjectKnowledge.

Rules:

1. Use only information contained in ProjectKnowledge.

2. Do not invent facts, requirements, stakeholders, risks,
   decisions, constraints, assumptions, or project details.

3. Preserve the meaning of all provided requirements.

4. You may rewrite information for clarity and professional
   BRD language.

5. You may synthesize information when constructing the
   executive summary, business requirements, and project scope,
   but the resulting content must remain supported by
   ProjectKnowledge.

6. Do not introduce technical decisions that are not present
   in ProjectKnowledge.

7. Do not remove meaningful requirements.

8. If information is unavailable, return an empty value or
   empty list instead of inventing information.

9. Preserve explicitly stated out-of-scope items, decisions,
   risks, assumptions, constraints, and open questions.

10. Return only the structured JSON requested by the schema.

ProjectKnowledge:

{project_knowledge_json}
"""
