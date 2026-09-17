from pathlib import Path
import re

from docx import Document

from app.ai.models.standard_document import StandardDocument
from app.ai.parsers.base import BaseParser
from app.core.config import settings


class DocxParser(BaseParser):
    """
    Parser for Microsoft Word (.docx) files.

    Supports normal Word documents as well as common meeting-transcript
    formats. Transcript documents are detected from their structure and
    metadata is extracted without changing the underlying transcript text.
    """

    SPEAKER_PATTERN = re.compile(
        r"^(?P<speaker>[^:\n]{1,100}):\s*(?P<content>.*)$"
    )

    URL_PATTERN = re.compile(
        r"^\s*https?://",
        re.IGNORECASE,
    )

    DURATION_PATTERN = re.compile(
        r"Meeting ended after\s+(?P<duration>\d{1,2}:\d{2}:\d{2})",
        re.IGNORECASE,
    )

    ATTENDEES_PATTERN = re.compile(
        r"Transcript Attendees\s+(?P<attendees>.+?)(?=\s+Transcript\b)",
        re.IGNORECASE | re.DOTALL,
    )

    def parse(
        self,
        source: str,
    ) -> list[StandardDocument]:
        file_path = Path(source)

        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {source}"
            )

        if file_path.suffix.lower() != ".docx":
            raise ValueError(
                "Expected a .docx file"
            )

        if file_path.stat().st_size > settings.max_upload_bytes:
            raise ValueError(
                f"File too large: {file_path.name} "
                f"(max {settings.max_upload_bytes // (1024 * 1024)}MB)"
            )

        document = Document(file_path)

        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        raw_content = "\n".join(paragraphs)

        is_transcript = self._is_transcript(raw_content)

        if is_transcript:
            content, transcript_metadata = self._parse_transcript(
                paragraphs=paragraphs,
                raw_content=raw_content,
            )
        else:
            content = raw_content
            transcript_metadata = {}

        if not content.strip():
            raise ValueError(
                f"No readable text found in: {file_path.name}"
            )

        if len(content) > settings.max_extracted_chars:
            raise ValueError(
                f"File content too large: {file_path.name} "
                f"(max {settings.max_extracted_chars} characters)"
            )

        metadata = {
            "file_name": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
            **transcript_metadata,
        }

        return [
            StandardDocument(
                source_type="docx",
                title=file_path.name,
                content=content,
                metadata=metadata,
            )
        ]

    @classmethod
    def _is_transcript(cls, content: str) -> bool:
        """
        Detect whether the document looks like a meeting transcript.

        Detection is intentionally conservative so normal DOCX files are
        not incorrectly classified as transcripts.
        """
        content_lower = content.lower()

        has_transcript_marker = (
            "transcript attendees" in content_lower
            or re.search(r"\btranscript\b", content_lower) is not None
        )

        has_speaker_turns = sum(
            1
            for line in content.splitlines()
            if not cls.URL_PATTERN.match(line)
            and cls.SPEAKER_PATTERN.match(line.strip())
        ) >= 2

        has_meeting_end_marker = (
            cls.DURATION_PATTERN.search(content) is not None
        )

        return (
            has_transcript_marker or has_meeting_end_marker
        ) and has_speaker_turns

    @classmethod
    def _parse_transcript(
        cls,
        paragraphs: list[str],
        raw_content: str,
    ) -> tuple[str, dict]:
        """
        Extract useful transcript content and lightweight metadata.

        The original spoken wording is preserved. This method only removes
        transcript-export metadata from the main content and normalizes
        speaker-labelled paragraphs.
        """
        metadata: dict = {
            "document_type": "transcript",
        }

        attendees = cls._extract_attendees(raw_content)

        if attendees:
            metadata["attendees"] = attendees

        duration = cls._extract_duration(raw_content)

        if duration:
            metadata["duration"] = duration

        content_paragraphs = cls._remove_transcript_metadata(paragraphs)

        content = cls._normalize_transcript_paragraphs(
            content_paragraphs
        )

        return content, metadata

    @classmethod
    def _extract_attendees(cls, content: str) -> list[str]:
        match = cls.ATTENDEES_PATTERN.search(content)

        if not match:
            return []

        attendees_text = match.group("attendees").strip()

        attendees = [
            attendee.strip()
            for attendee in re.split(r",|\n", attendees_text)
            if attendee.strip()
        ]

        return attendees

    @classmethod
    def _extract_duration(cls, content: str) -> str | None:
        match = cls.DURATION_PATTERN.search(content)

        if not match:
            return None

        return match.group("duration")

    @classmethod
    def _remove_transcript_metadata(
        cls,
        paragraphs: list[str],
    ) -> list[str]:
        """
        Remove common transcript-export header/footer content.

        The actual transcript turns are retained unchanged.
        """
        cleaned: list[str] = []

        skipping_attendee_header = False
        skipping_footer = False

        total = len(paragraphs)

        for index, paragraph in enumerate(paragraphs):
            text = paragraph.strip()

            if not text:
                continue

            lower_text = text.lower()

            if "transcript attendees" in lower_text:
                skipping_attendee_header = True

                if "transcript" in lower_text:
                    transcript_index = lower_text.find(
                        "transcript",
                        lower_text.find("transcript attendees")
                        + len("transcript attendees"),
                    )

                    if transcript_index != -1:
                        remaining = text[transcript_index + len("transcript") :].strip()

                        if remaining:
                            cleaned.append(remaining)

                        skipping_attendee_header = False

                continue

            if skipping_attendee_header:
                if lower_text == "transcript":
                    skipping_attendee_header = False

                continue

            if cls.DURATION_PATTERN.search(text):
                if index >= total - 5:
                    skipping_footer = True
                    continue

                cleaned.append(text)
                continue

            if skipping_footer:
                continue

            cleaned.append(text)

        return cleaned

    @classmethod
    def _normalize_transcript_paragraphs(
        cls,
        paragraphs: list[str],
    ) -> str:
        """
        Normalize speaker-labelled transcript paragraphs.

        Example:

            Monish K S:
            I see transcribing.

        becomes:

            Monish K S: I see transcribing.

        Existing speaker-labelled paragraphs are preserved as-is apart from
        whitespace normalization.
        """
        normalized: list[str] = []

        current_speaker: str | None = None
        current_content: list[str] = []

        def flush_current_speaker() -> None:
            nonlocal current_speaker
            nonlocal current_content

            if current_speaker is None:
                return

            speaker_content = " ".join(
                part.strip()
                for part in current_content
                if part.strip()
            )

            if speaker_content:
                normalized.append(
                    f"{current_speaker}: {speaker_content}"
                )
            else:
                normalized.append(
                    f"{current_speaker}:"
                )

            current_speaker = None
            current_content = []

        for paragraph in paragraphs:
            text = paragraph.strip()

            if not text:
                continue

            match = cls.SPEAKER_PATTERN.match(text)

            if match:
                flush_current_speaker()

                current_speaker = match.group("speaker").strip()
                speaker_content = match.group("content").strip()

                if speaker_content:
                    current_content.append(speaker_content)

                continue

            if current_speaker is not None:
                current_content.append(text)
            else:
                normalized.append(text)

        flush_current_speaker()

        return "\n\n".join(normalized)
