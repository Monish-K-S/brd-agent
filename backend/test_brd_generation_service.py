from services.indexing_service import IndexingService
from services.requirement_extraction_service import RequirementExtractionService
from services.brd_generation_service import BRDGenerationService


def print_requirements(result):
    print("=" * 70)
    print("EXTRACTED REQUIREMENTS")
    print("=" * 70)

    print(f"\nFunctional Requirements ({len(result.functional_requirements)})")
    print("-" * 70)

    if not result.functional_requirements:
        print("None")
    else:
        for i, requirement in enumerate(result.functional_requirements, 1):
            print(f"{i}. {requirement.description}")

    print(f"\nNon-Functional Requirements ({len(result.non_functional_requirements)})")
    print("-" * 70)

    if not result.non_functional_requirements:
        print("None")
    else:
        for i, requirement in enumerate(result.non_functional_requirements, 1):
            print(f"{i}. {requirement.description}")

    print()


def print_brd(brd):
    print("=" * 70)
    print("GENERATED BRD")
    print("=" * 70)

    print(f"\nProject Name:\n{brd.project_name}")

    print(f"\nExecutive Summary:\n{brd.executive_summary}")

    print("\nBusiness Objectives")
    print("-" * 70)

    if not brd.business_objectives:
        print("None")
    else:
        for objective in brd.business_objectives:
            print(f"- {objective}")

    print("\nFunctional Requirements")
    print("-" * 70)

    if not brd.functional_requirements:
        print("None")
    else:
        for requirement in brd.functional_requirements:
            print(f"- {requirement.description}")

    print("\nNon-Functional Requirements")
    print("-" * 70)

    if not brd.non_functional_requirements:
        print("None")
    else:
        for requirement in brd.non_functional_requirements:
            print(f"- {requirement.description}")


def main():
    print("=" * 70)
    print("INDEXING PROJECT")
    print("=" * 70)

    indexing_service = IndexingService()
    indexing_service.index_directory("../datasets/sample_project")

    print("Indexing completed.\n")

    print("=" * 70)
    print("EXTRACTING REQUIREMENTS")
    print("=" * 70)

    requirement_service = RequirementExtractionService()

    extraction_result = requirement_service.extract(
        query="Generate business requirements for this project."
    )

    print_requirements(extraction_result)

    print("=" * 70)
    print("GENERATING BRD")
    print("=" * 70)

    brd_service = BRDGenerationService()

    brd = brd_service.generate(extraction_result)

    print_brd(brd)


if __name__ == "__main__":
    main()
