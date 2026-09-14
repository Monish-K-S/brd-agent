import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

from bs4 import BeautifulSoup

from app.ai.models.standard_document import StandardDocument


class GmailEmailMapper:
    """
    Maps Gmail API message responses into the internal
    AI StandardDocument representation.

    This class is responsible only for transforming Gmail
    data. It does not interact with the database.
    """

    def to_standard_document(
        self,
        message: dict,
    ) -> StandardDocument:
        payload = message.get("payload", {})

        headers = self._extract_headers(
            payload.get("headers", []),
        )

        content = self._extract_content(
            payload,
        )

        participants = self._extract_participants(
            headers,
        )

        source_created_at = self._parse_date(
            headers.get("date"),
        )

        metadata = {
            "gmail_message_id": message.get("id"),
            "gmail_thread_id": message.get("threadId"),
        }

        return StandardDocument(
            source_type="email",
            title=headers.get("subject"),
            author=headers.get("from"),
            source_created_at=source_created_at,
            participants=participants,
            content=content,
            metadata=metadata,
        )

    def _extract_headers(
        self,
        headers: list[dict],
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        for header in headers:
            name = header.get("name")
            value = header.get("value")

            if not name or value is None:
                continue

            result[name.lower()] = value

        return result

    def _extract_participants(
        self,
        headers: dict[str, str],
    ) -> list[str]:
        participants: list[str] = []

        for header_name in ("from", "to", "cc"):
            value = headers.get(header_name)

            if not value:
                continue

            participants.extend(
                self._split_addresses(value),
            )

        return self._unique_preserving_order(
            participants,
        )

    def _split_addresses(
        self,
        value: str,
    ) -> list[str]:
        addresses = []

        for part in value.split(","):
            part = part.strip()

            if part:
                addresses.append(part)

        return addresses

    def _extract_content(
        self,
        payload: dict,
    ) -> str:
        plain_text = self._find_body_part(
            payload,
            "text/plain",
        )

        if plain_text:
            return self._clean_text(plain_text)

        html = self._find_body_part(
            payload,
            "text/html",
        )

        if html:
            return self._html_to_text(html)

        return ""

    def _find_body_part(
        self,
        part: dict,
        mime_type: str,
    ) -> str | None:
        current_mime_type = part.get("mimeType")

        if current_mime_type == mime_type:
            body = part.get("body", {})
            data = body.get("data")

            if data:
                return self._decode_body(data)

        for child in part.get("parts", []) or []:
            content = self._find_body_part(
                child,
                mime_type,
            )

            if content:
                return content

        return None

    def _decode_body(
        self,
        data: str,
    ) -> str:
        decoded = base64.urlsafe_b64decode(
            data + "=" * (-len(data) % 4),
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    def _html_to_text(
        self,
        html: str,
    ) -> str:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        text = soup.get_text(
            "\n",
            strip=True,
        )

        return self._clean_text(text)

    def _clean_text(
        self,
        text: str,
    ) -> str:
        """
        Decode HTML entities that may remain in the extracted
        email content.

        Handles both normal and double-encoded entities, e.g.:

            &#39;       -> '
            &amp;        -> &
            &amp;#39;    -> &#39; -> '
        """

        for _ in range(2):
            decoded = unescape(text)

            if decoded == text:
                break

            text = decoded

        return text

    def _parse_date(
        self,
        value: str | None,
    ) -> datetime | None:
        if not value:
            return None

        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

    def _unique_preserving_order(
        self,
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            result.append(value)

        return result

    def to_message_summary(
        self,
        message: dict,
    ) -> dict:
        payload = message.get("payload", {})

        headers = self._extract_headers(
            payload.get("headers", []),
        )

        return {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "subject": headers.get("subject"),
            "sender": headers.get("from"),
            "date": self._parse_date(
                headers.get("date"),
            ),
            "snippet": self._clean_text(
                message.get("snippet", ""),
            ),
        }
