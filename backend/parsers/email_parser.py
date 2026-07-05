from email import policy
from email.parser import Parser
from email.utils import parsedate_to_datetime
from pathlib import Path

from models.standard_document import StandardDocument
from parsers.base import BaseParser


class EmailParser(BaseParser):
    """
    Parser for standard .eml email files.
    """

    def parse(self, source: str) -> list[StandardDocument]:
        file_path = Path(source)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {source}")

        if file_path.suffix.lower() != ".eml":
            raise ValueError("Expected a .eml file")

        raw_email = file_path.read_text(encoding="utf-8")

        email = Parser(policy=policy.default).parsestr(raw_email)

        author = email.get("From")
        subject = email.get("Subject")
        date = email.get("Date")

        created_at = None
        if date:
            try:
                created_at = parsedate_to_datetime(date)
            except Exception:
                pass

        to = email.get_all("To", [])
        cc = email.get_all("Cc", [])
        bcc = email.get_all("Bcc", [])

        participants = []

        if author:
            participants.append(author)

        for group in (to, cc, bcc):
            for item in group:
                participants.extend(
                    [addr.strip() for addr in item.split(",") if addr.strip()]
                )

        body = ""

        plain_body = email.get_body(preferencelist=("plain",))

        if plain_body:
            body = plain_body.get_content()
        else:
            payload = email.get_payload()

            if isinstance(payload, str):
                body = payload

        return [
            StandardDocument(
                source_type="email",
                title=subject,
                author=author,
                created_at=created_at,
                participants=participants,
                content=body,
                metadata={
                    "message_id": email.get("Message-ID"),
                    "to": to,
                    "cc": cc,
                    "bcc": bcc,
                    "file_name": file_path.name,
                },
            )
        ]
