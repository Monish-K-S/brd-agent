import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")

if not API_KEY:
    raise RuntimeError("SARVAM_API_KEY is not set")

PDF_PATH = Path("output/sample_project.pdf")
SCHEMA_PATH = Path(
    "extractors/schemas/document_knowledge_schema.json"
)


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    client = SarvamAI(
        api_subscription_key=API_KEY,
    )

    with PDF_PATH.open("rb") as file:
        job = client.doc_ai.extract(
            file=[
                (
                    PDF_PATH.name,
                    file,
                    "application/pdf",
                )
            ],
            schema=json.dumps(schema),
            language="en-IN",
            output_format="json",
        )

    print("Job created")
    print("Job ID:", job.job_id)
    print("Status:", job.status)


if __name__ == "__main__":
    main()
