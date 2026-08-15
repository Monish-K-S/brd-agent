import json
from pathlib import Path

from extractors.sarvam_extractor import SarvamExtractor


PDF_PATH = Path("output/sample_project.pdf")
SCHEMA_PATH = Path(
    "extractors/schemas/document_knowledge_schema.json"
)
OUTPUT_PATH = Path("output/sarvam_extraction.json")


def main() -> None:
    extractor = SarvamExtractor(
        schema_path=SCHEMA_PATH,
    )

    result = extractor.extract(
        pdf_path=PDF_PATH,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"Extraction result saved to: "
        f"{OUTPUT_PATH.resolve()}"
    )


if __name__ == "__main__":
    main()
