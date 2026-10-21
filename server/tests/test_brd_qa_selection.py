"""Q&A source selection (P-9).

``_score_document`` used to tokenize the entire document into a set of
every distinct word, intersect it with the question's terms, then throw
the set away — per document, per question. On a workspace at the
documented cap (10 files x 500k chars) that is roughly 5M characters
tokenized to answer a question about at most a handful of words.

The replacement scans for the question's terms directly. Its whole
justification is that the **selection is unchanged**, so these tests are
written as an equivalence proof against the old algorithm rather than as
a description of the new one:

- ``_LegacySelector`` below is the previous implementation, kept here as
  an oracle. Every test compares the new code against it.
- The corpus is deliberately hostile: underscores, hyphens, decimals,
  substrings, accented text, repeated tokens, punctuation and empty
  content — the places where a naive ``\\b`` regex would silently diverge
  from ``[a-zA-Z0-9]+`` tokenization.

If someone later "simplifies" the boundary handling to ``\\b``, the
underscore cases fail.
"""

import random
import re
from uuid import uuid4

import pytest

from app.db.models.standard_document import StandardDocument
from app.services.brd_qa_service import BRDQAService


class _LegacySelector:
    """The pre-P-9 scoring algorithm, unchanged, as a test oracle."""

    @staticmethod
    def score(question_terms: set[str], document) -> int:
        title_terms = BRDQAService._tokenize(document.title or "")
        content_terms = BRDQAService._tokenize(document.content or "")

        score = 0

        for term in question_terms:
            if term in title_terms:
                score += 5

            if term in content_terms:
                score += 1

        return score

    @classmethod
    def select(cls, question: str, documents: list) -> list:
        """Full copy of the old ``_select_relevant_documents``."""

        if not documents:
            return []

        question_terms = BRDQAService._tokenize(question)

        if not question_terms:
            return documents[: BRDQAService.MAX_RELEVANT_SOURCES]

        scored = [
            (cls.score(question_terms, document), index, document)
            for index, document in enumerate(documents)
        ]

        relevant = [
            item
            for item in scored
            if item[0] >= BRDQAService.MIN_RELEVANCE_SCORE
        ]

        relevant.sort(key=lambda item: (-item[0], item[1]))

        if relevant:
            return [
                item[2]
                for item in relevant[: BRDQAService.MAX_RELEVANT_SOURCES]
            ]

        scored.sort(key=lambda item: item[1])

        return [
            item[2]
            for item in scored[: BRDQAService.MAX_RELEVANT_SOURCES]
        ]


def _document(title: str, content: str) -> StandardDocument:
    return StandardDocument(
        id=uuid4(),
        workspace_id=uuid4(),
        source_type="txt",
        title=title,
        content=content,
    )


# ------------------------------------------------ score equivalence


SHARED_CORPUS = [
    ("Requirements", ""),
    ("Requirements", "foo_bar baz"),
    ("Requirements", "3.5 seconds and 35 seconds"),
    ("Requirements", "cafe resumes and naive text"),
    ("Requirements", "caf\u00e9 r\u00e9sum\u00e9 na\u00efve"),
    ("Requirements", "foobar foo fo"),
    ("UPPER", "lower MiXeD CaSe"),
    ("Requirements", "multi-word-token"),
    ("Requirements", "tab\tseparated\nnewline"),
    ("Requirements", "duplicate duplicate duplicate"),
    ("Requirements", "question? marks! quotes' here"),
    ("Requirements", "x1 x2 x12 xx 1x"),
    ("Requirements", "a\u2014b a\u2013b a-b"),
    ("Requirements", "alpha.beta gamma:delta"),
    ("Requirements", "   "),
    ("Requirements", "login login; Login LOGIN"),
]


@pytest.mark.parametrize(
    ("question_terms"),
    [
        {"foo"},
        {"foo", "foobar"},
        {"3", "35"},
        {"caf"},
        {"caf\u00e9"},
        {"baz", "bar"},
        {"uppercase"},
        {"upper"},
        {"x1", "x12", "xx"},
        {"login"},
        {"requirement"},
        {"a", "b"},
        {"text"},
        {"seconds"},
    ],
)
def test_score_matches_legacy_for_every_corpus_row(question_terms):
    for title, content in SHARED_CORPUS:
        document = _document(title, content)

        assert BRDQAService._score_document(
            question_terms,
            document,
        ) == _LegacySelector.score(question_terms, document)


def test_score_matches_legacy_on_random_token_soup():
    # Deterministic (seeded) fuzz over the characters that separate
    # tokens, so a boundary regression cannot hide behind curated cases.
    rng = random.Random(20261021)

    alphabet = (
        list("abcABC012") + ["_", "-", ".", " ", "?", "\t", "\u00e9", "\u2014"]
    )

    for _ in range(300):
        content = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
        terms = {
            "".join(rng.choice(list("ab01")) for _ in range(rng.randint(1, 4)))
            for _ in range(rng.randint(1, 3))
        }

        document = _document("Mixed", content)

        assert BRDQAService._score_document(
            terms,
            document,
        ) == _LegacySelector.score(terms, document), (
            f"divergence on {content!r} with terms {terms}"
        )


# ------------------------------------------------ selection equivalence


def _workspace() -> list[StandardDocument]:
    return [
        _document(
            "Requirements",
            "Users can log in with Google. Sessions expire after 30 minutes.",
        ),
        _document(
            "Design notes",
            "The login screen shows a single Google button.",
        ),
        _document(
            "Meeting transcript",
            "We discussed pricing, headcount and the office move.",
        ),
        _document(
            "Login",
            "Unrelated content about parking.",
        ),
        _document(
            "Support runbook",
            "If login fails, check the OAuth client redirect URI.",
        ),
        _document("Requirements", "Export the BRD to PDF or DOCX."),
        _document("Sales deck", "Pipeline coverage and quotas."),
        _document("Login notes", "Sessions expire after 30 minutes."),
        _document("Roadmap", "Q1 login, Q2 exports, Q3 billing."),
        _document("Glossary", "BRD means business requirements document."),
        _document("Misc", "Nothing relevant here."),
    ]


SELECTION_QUESTIONS = [
    "How do users log in?",
    "What happens when sessions expire?",
    "How do I export the BRD?",
    "Tell me about the office move",
    "the and of",  # every term is a stop word -> early fallback
    "zebra xylophone",  # no lexical match -> deterministic fallback
    "login",
    "Which OAuth redirect URI should I check?",
]


@pytest.mark.parametrize("question", SELECTION_QUESTIONS)
def test_selection_matches_legacy(question):
    documents = _workspace()

    assert [
        document.id
        for document in BRDQAService._select_relevant_documents(
            question,
            documents,
        )
    ] == [
        document.id
        for document in _LegacySelector.select(question, documents)
    ]


def test_relevant_documents_are_ordered_by_score_then_position():
    documents = _workspace()

    selected = BRDQAService._select_relevant_documents(
        "login",
        documents,
    )

    # "Login" (title match) and "Login notes" outrank content-only hits.
    assert [document.title for document in selected[:2]] == [
        "Login",
        "Login notes",
    ]


def test_fallback_returns_the_first_documents_when_nothing_matches():
    documents = _workspace()

    selected = BRDQAService._select_relevant_documents(
        "zebra xylophone",
        documents,
    )

    assert selected == documents[: BRDQAService.MAX_RELEVANT_SOURCES]


def test_at_most_max_relevant_sources_are_returned():
    documents = [
        _document(f"Doc {index}", "login login login")
        for index in range(20)
    ]

    selected = BRDQAService._select_relevant_documents(
        "login",
        documents,
    )

    assert len(selected) == BRDQAService.MAX_RELEVANT_SOURCES


def test_empty_workspace_selects_nothing():
    assert BRDQAService._select_relevant_documents("login", []) == []


# ------------------------------------------------ cost guard


def test_term_pattern_treats_underscore_as_a_separator():
    # `_tokenize` splits on [a-zA-Z0-9]+, so `foo_bar` contains `foo`.
    # `\bfoo\b` would say it does not, because `_` is a word character.
    pattern = BRDQAService._term_pattern({"foo"})

    assert pattern.search("foo_bar") is not None
    assert pattern.search("foobar") is None
    assert pattern.search("xfoo") is None


def test_count_present_terms_stops_early_on_large_text():
    # Not a timing assertion — just proof that the happy path returns
    # the same answer on a string far larger than any real document.
    text = " ".join(["padding"] * 50_000) + " login"
    terms = {"login", "padding"}

    assert BRDQAService._count_present_terms(terms, text) == 2

    pattern = BRDQAService._term_pattern(terms)

    assert (
        BRDQAService._count_present_terms(
            terms,
            text,
            pattern=pattern,
        )
        == 2
    )
