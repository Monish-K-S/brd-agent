import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")

if not API_KEY:
    raise RuntimeError("SARVAM_API_KEY is not set")

JOB_ID = "01a00093-d2c2-7d9a-8c0c-26d4a15e7548"

OUTPUT_PATH = Path("output/sarvam_extraction.json")


def main() -> None:
    client = SarvamAI(
        api_subscription_key=API_KEY,
    )

    result = client.doc_ai.get_results(
        job_id=JOB_ID,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Convert the SDK response into normal JSON-serializable data.
    if hasattr(result, "model_dump"):
        result_data = result.model_dump(mode="json")
    else:
        result_data = result

    OUTPUT_PATH.write_text(
        json.dumps(
            result_data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"Result saved to: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
