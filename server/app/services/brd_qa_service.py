import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.generators.gemini_brd_qa_generator import (
    GeminiBRDQAGenerator,
)
from app.db.models.standard_document import StandardDocument
from app.repositories.brd_repository import BRDRepository
from app.repositories.standard_document_repository import (
    StandardDocumentRepository,
)
from app.services.project_knowledge_service import (
    ProjectKnowledgeService,
)
from app.services.workspace_service import WorkspaceService


class BRDQAService:
    MAX_RELEVANT_SOURCES = 8
    MAX_SOURCE_CONTENT_LENGTH = 12000
    MIN_RELEVANCE_SCORE = 2

    # Shared by `_tokenize` (indexing) and `_is_indexable_term`
    # (scanning), so the two can never disagree about which words count.
    MIN_TERM_LENGTH = 3

    STOP_WORDS = frozenset(
        {
            "a",
            "about",
            "an",
            "and",
            "are",
            "be",
            "can",
            "do",
            "does",
            "for",
            "from",
            "how",
            "i",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "our",
            "the",
            "this",
            "to",
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "with",
            "you",
            "your",
        }
    )

    # A single token, as `_tokenize` produces them.
    _TERM_RUN = re.compile(r"[a-zA-Z0-9]+\Z")

    def __init__(self, db: Session):
        self.db = db

        self.brd_repository = BRDRepository(db)

        self.standard_document_repository = StandardDocumentRepository(db)

        self.project_knowledge_service = ProjectKnowledgeService(db)

        self.workspace_service = WorkspaceService(db)

        self.qa_generator = GeminiBRDQAGenerator()

    def answer_question_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        question: str,
    ) -> dict | None:
        workspace = self.workspace_service.get_workspace_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        if workspace is None:
            return None

        brd = self.brd_repository.get_by_workspace_id(
            workspace_id,
        )

        project_knowledge = (
            self.project_knowledge_service.get_project_knowledge_for_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )
        )

        if brd is None and project_knowledge is None:
            return {
                "answer": (
                    "There is no BRD or project knowledge available "
                    "for this workspace yet."
                ),
                "sources": [],
            }

        source_documents = (
            self.standard_document_repository.get_all_by_workspace_id(
                workspace_id,
            )
        )

        brd_data = (
            brd.brd_data
            if brd is not None
            else {}
        )

        project_knowledge_data = (
            project_knowledge.knowledge_data
            if project_knowledge is not None
            else {}
        )

        relevant_documents = self._select_relevant_documents(
            question=question,
            documents=source_documents,
        )

        source_context = [
            self._serialize_source_document(
                document,
            )
            for document in relevant_documents
        ]

        generated_response = self.qa_generator.answer(
            question=question,
            brd_data=brd_data,
            project_knowledge=project_knowledge_data,
            source_documents=source_context,
        )

        valid_source_ids = self._validate_source_ids(
            source_documents=source_documents,
            source_ids=generated_response["source_ids"],
        )

        sources = [
            self._serialize_source_reference(
                document,
            )
            for document in source_documents
            if str(document.id) in valid_source_ids
        ]

        return {
            "answer": generated_response["answer"],
            "sources": sources,
        }

    @classmethod
    def _select_relevant_documents(
        cls,
        question: str,
        documents: list[StandardDocument],
    ) -> list[StandardDocument]:
        if not documents:
            return []

        question_terms = cls._tokenize(question)

        if not question_terms:
            return documents[: cls.MAX_RELEVANT_SOURCES]

        content_pattern = cls._term_pattern(question_terms)

        scored_documents: list[
            tuple[int, int, StandardDocument]
        ] = []

        for index, document in enumerate(documents):
            score = cls._score_document(
                question_terms=question_terms,
                content_pattern=content_pattern,
                document=document,
            )

            scored_documents.append(
                (
                    score,
                    index,
                    document,
                )
            )

        relevant_documents = [
            item
            for item in scored_documents
            if item[0] >= cls.MIN_RELEVANCE_SCORE
        ]

        relevant_documents.sort(
            key=lambda item: (-item[0], item[1]),
        )

        if relevant_documents:
            return [
                item[2]
                for item in relevant_documents[
                    : cls.MAX_RELEVANT_SOURCES
                ]
            ]

        # No meaningful lexical match.
        # Include a small deterministic fallback so Gemini can still
        # answer questions whose wording differs from the source text.
        scored_documents.sort(
            key=lambda item: item[1],
        )

        return [
            item[2]
            for item in scored_documents[
                : cls.MAX_RELEVANT_SOURCES
            ]
        ]

    @classmethod
    def _score_document(
        cls,
        question_terms: set[str],
        document: StandardDocument,
        content_pattern: re.Pattern[str] | None = None,
    ) -> int:
        title_terms = cls._tokenize(
            document.title or "",
        )

        score = 5 * len(question_terms & title_terms)

        score += cls._count_present_terms(
            terms=question_terms,
            text=document.content or "",
            pattern=content_pattern,
        )

        return score

    @classmethod
    def _count_present_terms(
        cls,
        terms: set[str],
        text: str,
        pattern: re.Pattern[str] | None = None,
    ) -> int:
        """Count how many of ``terms`` occur in ``text`` as whole tokens.

        This used to tokenize the entire document into a set of every
        distinct word, intersect it with the question's terms, and throw
        the set away — allocating a set of hundreds of thousands of
        strings per document, per question, to answer a question about
        at most a handful of words.

        The result is identical, because a term is present exactly when
        it is a maximal ``[a-zA-Z0-9]+`` run **and** survives the same
        filter ``_tokenize`` applies when building its set (min length
        and stop words). Terms that the old set could never have
        contained are excluded up front rather than scanned for.

        The scan also stops as soon as every eligible term has been seen.
        """

        eligible = {
            term
            for term in terms
            if cls._is_indexable_term(term)
        }

        if not eligible:
            return 0

        lowered = text.lower()

        if not lowered:
            return 0

        if pattern is None:
            pattern = cls._term_pattern(eligible)

        found: set[str] = set()

        for match in pattern.finditer(lowered):
            found.add(match.group(0))

            if len(found) == len(eligible):
                break

        return len(found)

    @classmethod
    def _is_indexable_term(cls, term: str) -> bool:
        return (
            len(term) >= cls.MIN_TERM_LENGTH
            and term not in cls.STOP_WORDS
            # Tokens are lowercased maximal `[a-zA-Z0-9]` runs, so a term
            # containing anything else, or uppercase, can never equal
            # one. `_tokenize` guarantees this for real questions; the
            # check keeps the function honest for any caller.
            and term == term.lower()
            and cls._TERM_RUN.fullmatch(term) is not None
        )

    @staticmethod
    def _term_pattern(terms: set[str]) -> re.Pattern[str]:
        """Match any of ``terms`` as a whole token.

        Longest-first ordering keeps an alternation from settling on a
        prefix of a longer term and then failing the trailing boundary.

        Lookarounds rather than ``\\b`` on purpose: ``\\b`` treats ``_``
        as a word character, but ``_tokenize`` splits on
        ``[a-zA-Z0-9]+``, so ``foo_bar`` contains the token ``foo``.
        """

        alternatives = "|".join(
            re.escape(term)
            for term in sorted(
                terms,
                key=len,
                reverse=True,
            )
        )

        return re.compile(
            rf"(?<![a-zA-Z0-9])(?:{alternatives})(?![a-zA-Z0-9])"
        )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        return {
            word
            for word in words
            if len(word) >= BRDQAService.MIN_TERM_LENGTH
            and word not in BRDQAService.STOP_WORDS
        }

    @classmethod
    def _serialize_source_document(
        cls,
        document: StandardDocument,
    ) -> dict:
        content = document.content or ""

        if len(content) > cls.MAX_SOURCE_CONTENT_LENGTH:
            content = (
                content[: cls.MAX_SOURCE_CONTENT_LENGTH]
                + "\n\n[Source content truncated for Q&A context.]"
            )

        return {
            "id": str(document.id),
            "title": document.title,
            "source_type": document.source_type,
            "author": document.author,
            "source_created_at": (
                document.source_created_at.isoformat()
                if document.source_created_at
                else None
            ),
            "participants": document.participants,
            "content": content,
        }

    @staticmethod
    def _serialize_source_reference(
        document: StandardDocument,
    ) -> dict:
        return {
            "id": document.id,
            "title": document.title,
            "source_type": document.source_type,
        }

    @staticmethod
    def _validate_source_ids(
        source_documents: list[StandardDocument],
        source_ids: list[str],
    ) -> set[str]:
        available_ids = {
            str(document.id)
            for document in source_documents
        }

        return {
            source_id
            for source_id in source_ids
            if source_id in available_ids
        }
