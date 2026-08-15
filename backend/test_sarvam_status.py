import os

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")

if not API_KEY:
    raise RuntimeError("SARVAM_API_KEY is not set")

JOB_ID = "01a00093-d2c2-7d9a-8c0c-26d4a15e7548"


def main() -> None:
    client = SarvamAI(
        api_subscription_key=API_KEY,
    )

    status = client.doc_ai.get_status(
        job_id=JOB_ID,
    )

    print("Job ID:", JOB_ID)
    print("Status:", status)


if __name__ == "__main__":
    main()
