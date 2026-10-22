"""Tokenization shared by the metrics.

"Content word" is defined once, in ``BRDQAService``, and reused here. The
Q&A service already had to decide which words are worth matching on
(``MIN_TERM_LENGTH`` and ``STOP_WORDS``); inventing a second definition
for the evaluator would let the two drift, and the resulting scores would
be measuring two different things.
"""

import re

from app.services.brd_qa_service import BRDQAService

MIN_TERM_LENGTH = BRDQAService.MIN_TERM_LENGTH
STOP_WORDS = BRDQAService.STOP_WORDS

_WORD = re.compile(r"[a-zA-Z0-9]+")


def normalize(text: object) -> str:
    """Collapse whitespace and lowercase — nothing else.

    Deliberately conservative: digits and punctuation survive, so a
    requirement that changes a threshold cannot be normalized into a
    different one.
    """
    if not isinstance(text, str):
        return ""

    return " ".join(text.split()).lower()


def tokenize(text: object) -> list[str]:
    """Split text into content words, preserving repetition."""
    if not isinstance(text, str):
        return []

    return [
        word
        for word in _WORD.findall(text.lower())
        if len(word) >= MIN_TERM_LENGTH and word not in STOP_WORDS
    ]


def content_words(text: object) -> set[str]:
    """Distinct content words in ``text``."""
    return set(tokenize(text))
