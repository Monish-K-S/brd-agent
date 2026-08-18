from pathlib import Path

from services.brd_pipeline import BrdPipeline


SAMPLE_PROJECT_DIR = Path(
    "../datasets/sample_project"
)

DOCUMENT_KNOWLEDGE_SCHEMA = Path(
    "extractors/schemas/document_knowledge_schema.json"
)

BRD_SCHEMA = Path(
    "generators/schemas/brd_schema.json"
)

OUTPUT_PATH = Path(
    "output/customer_support_portal_brd.pdf"
)


def main() -> None:
    pipeline = BrdPipeline(
        document_knowledge_schema_path=(
            DOCUMENT_KNOWLEDGE_SCHEMA
        ),
        brd_schema_path=BRD_SCHEMA,
    )

    brd = pipeline.generate(
        source_directory=SAMPLE_PROJECT_DIR,
        output_pdf_path=OUTPUT_PATH,
    )

    print(
        "BRD generated successfully."
    )

    print(
        f"Output: {OUTPUT_PATH.resolve()}"
    )

    print(
        f"Project: "
        f"{brd.project_overview.project_name}"
    )


if __name__ == "__main__":
    main()
