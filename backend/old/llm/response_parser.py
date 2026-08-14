from uuid import UUID
from models.brd import BRD
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


    def parse_brd(
        self,
        response: dict,
        requirements: RequirementExtractionResult,
    ) -> BRD:
        """
        Convert Gemini's BRD JSON into a BRD Domain Model.
        """

        return BRD(
            project_name=response["project_name"],
            executive_summary=response["executive_summary"],
            business_objectives=response["business_objectives"],
            functional_requirements=requirements.functional_requirements,
            non_functional_requirements=requirements.non_functional_requirements,
        )
