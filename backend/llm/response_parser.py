from uuid import UUID
from models.requirement import Requirement
from models.requirement_extraction_result import RequirementExtractionResult


class ResponseParser:
    """
    Convert Gemini responses into Requirement objects.
    """


    def parse(
        self,
        response: dict,
        source_chunk_ids: list[UUID],
        ) -> RequirementExtractionResult:

            functional_requirements = [
                Requirement(
                    requirement_type="functional",
                    description=requirement["description"],
                    source_chunk_ids=source_chunk_ids,
                )
                for requirement in response["functional_requirements"]
            ]

            non_functional_requirements = [
                Requirement(
                    requirement_type="non_functional",
                    description=requirement["description"],
                    source_chunk_ids=source_chunk_ids,
                )
                for requirement in response["non_functional_requirements"]
            ]


            return RequirementExtractionResult(
                functional_requirements=functional_requirements,
                non_functional_requirements=non_functional_requirements,
            )
