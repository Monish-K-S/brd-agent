import json
import logging
import math
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

from app.core.config import settings

logger = logging.getLogger("brd-agent.extraction")


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
        timeout_seconds: int | None = None,
    ) -> None:
        load_dotenv()

        api_key = os.getenv("SARVAM_API_KEY")

        if not api_key:
            raise RuntimeError(
                "SARVAM_API_KEY is not set"
            )

        self.client = SarvamAI(
            api_subscription_key=api_key,
        )

        self.schema_path = Path(schema_path)

        # Ceiling for one extraction job. Configurable because a large
        # aggregate PDF can legitimately exceed the old hardcoded 60x2s;
        # timing it out there lost the whole generation (P-3).
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.sarvam_timeout_seconds
        )

    @property
    def max_attempts(self) -> int:
        return max(
            1,
            math.ceil(
                self.timeout_seconds / self.POLL_INTERVAL_SECONDS
            ),
        )

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

        logger.info(
            "Submitted Sarvam extraction job %s (%s)",
            job.job_id,
            pdf_path.name,
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
        max_attempts = self.max_attempts
        started = time.perf_counter()

        for attempt in range(1, max_attempts + 1):
            status = self.client.doc_ai.get_status(
                job_id=job_id,
            )

            if status.status == "completed":
                logger.info(
                    "Sarvam job %s completed after %s poll(s) in %.1fs",
                    job_id,
                    attempt,
                    time.perf_counter() - started,
                )

                return

            if status.status in {
                "failed",
                "cancelled",
            }:
                logger.warning(
                    "Sarvam job %s ended as %s after %s poll(s)",
                    job_id,
                    status.status,
                    attempt,
                )

                raise RuntimeError(
                    f"Sarvam extraction failed. "
                    f"Job ID: {job_id}, "
                    f"Status: {status.status}"
                )

            if attempt < max_attempts:
                time.sleep(
                    self.POLL_INTERVAL_SECONDS,
                )

        logger.warning(
            "Sarvam job %s timed out after %s poll(s) (~%ss)",
            job_id,
            max_attempts,
            self.timeout_seconds,
        )

        raise TimeoutError(
            f"Sarvam extraction timed out after "
            f"{self.timeout_seconds}s. Job ID: {job_id}"
        )

    def _get_results(
        self,
        job_id: str,
    ) -> dict:
        result = self.client.doc_ai.get_results(
            job_id=job_id,
        )

        if hasattr(result, "model_dump"):
            return result.model_dump(
                mode="json",
            )

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

    def _load_schema(
        self,
    ) -> dict:
        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"Schema not found: {self.schema_path}"
            )

        return json.loads(
            self.schema_path.read_text(
                encoding="utf-8",
            )
        )

    @staticmethod
    def _validate_inputs(
        pdf_path: Path,
    ) -> None:
        if not pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                "Expected a PDF file"
            )
