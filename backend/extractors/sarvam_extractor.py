import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI


class SarvamExtractor:
    """
    Extracts structured project knowledge from a PDF using
    Sarvam Document AI.
    """

    LANGUAGE = "en-IN"
    OUTPUT_FORMAT = "json"

    POLL_INTERVAL_SECONDS = 2

    def __init__(
        self,
        schema_path: str | Path,
    ) -> None:
        load_dotenv()

        api_key = os.getenv("SARVAM_API_KEY")

        if not api_key:
            raise RuntimeError("SARVAM_API_KEY is not set")

        self.client = SarvamAI(
            api_subscription_key=api_key,
        )

        self.schema_path = Path(schema_path)

    def extract(
        self,
        pdf_path: str | Path,
        output_path: str | Path | None = None,
    ) -> dict:
        """
        Submit a PDF to Sarvam Document AI and return
        the completed extraction result.

        If output_path is provided, the raw Sarvam response
        is also saved as a JSON file.
        """

        pdf_path = Path(pdf_path)

        self._validate_inputs(pdf_path)

        schema = self._load_schema()

        job = self._create_job(
            pdf_path=pdf_path,
            schema=schema,
        )

        self._wait_for_completion(
            job_id=job.job_id,
        )

        result = self._get_results(
            job_id=job.job_id,
        )

        if output_path is not None:
            self._save_result(
                result=result,
                output_path=output_path,
            )

        return result

    def _create_job(
        self,
        pdf_path: Path,
        schema: dict,
    ):
        with pdf_path.open("rb") as file:
            return self.client.doc_ai.extract(
                file=[
                    (
                        pdf_path.name,
                        file,
                        "application/pdf",
                    )
                ],
                schema=json.dumps(schema),
                language=self.LANGUAGE,
                output_format=self.OUTPUT_FORMAT,
            )

    def _wait_for_completion(
        self,
        job_id: str,
    ) -> None:
        while True:
            status = self.client.doc_ai.get_status(
                job_id=job_id,
            )

            if status.status == "completed":
                return

            if status.status in {
                "failed",
                "cancelled",
            }:
                raise RuntimeError(
                    f"Sarvam extraction failed. "
                    f"Job ID: {job_id}, "
                    f"Status: {status.status}"
                )

            time.sleep(self.POLL_INTERVAL_SECONDS)

    def _get_results(
        self,
        job_id: str,
    ) -> dict:
        result = self.client.doc_ai.get_results(
            job_id=job_id,
        )

        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")

        return result

    def _save_result(
        self,
        result: dict,
        output_path: str | Path,
    ) -> None:
        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _load_schema(self) -> dict:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {self.schema_path}")

        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_inputs(
        pdf_path: Path,
    ) -> None:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Expected a PDF file")
