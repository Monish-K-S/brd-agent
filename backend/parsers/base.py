from abc import ABC, abstractmethod

from models.standard_document import StandardDocument


class BaseParser(ABC):
    """
    Base class for all document parsers.

    Every parser must convert an external source into a StandardDocument.

    """

    @abstractmethod
    def parse(self, source: str) -> list[StandardDocument]:
        """
        Parse the given source and return one or StandardDocuments.
        """

        raise NotImplementedError
