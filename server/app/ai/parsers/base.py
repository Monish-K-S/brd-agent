from abc import ABC, abstractmethod

from app.ai.models.standard_document import StandardDocument


class BaseParser(ABC):
    """
    Base class for all document parsers.

    Every parser converts an external source into one or more
    StandardDocument objects.
    """

    @abstractmethod
    def parse(
        self,
        source: str,
    ) -> list[StandardDocument]:
        """
        Parse the given source and return one or more StandardDocuments.
        """

        raise NotImplementedError
