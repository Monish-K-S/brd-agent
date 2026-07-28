import json
from typing import Any

from models.standard_document import StandardDocument


REQUIRED_KEYS = (
    "project_information",
    "stakeholders",
    "business_objectives",
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "assumptions",
    "decisions",
    "risks",
    "open_questions",
)


class ResponseParserError(Exception):
    """Raised when an LLM response cannot be parsed."""


class ResponseParser:
    """Parses LLM responses."""

    def parse_document_analysis(
        self,
        response: str,
    ) -> dict[str, Any]:
        """
        Parse and validate an LLM response.

        Returns the validated JSON dictionary.
        """

        data = self._load_json(response)

        self._validate_schema(data)

        return data

    def _load_json(
        self,
        response: str,
    ) -> dict[str, Any]:
        """
        Convert the raw LLM response into a Python dictionary.
        """

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ResponseParserError(
                "Invalid JSON returned by the LLM."
            ) from e

        if not isinstance(data, dict):
            raise ResponseParserError(
                "LLM response must be a JSON object."
            )

        return data

    def _validate_schema(
        self,
        data: dict[str, Any],
    ) -> None:
        """
        Validate the top-level extraction schema.
        """

        missing_keys = [
            key
            for key in REQUIRED_KEYS
            if key not in data
        ]

        if missing_keys:
            raise ResponseParserError(
                "Missing required keys: "
                + ", ".join(missing_keys)
            )
