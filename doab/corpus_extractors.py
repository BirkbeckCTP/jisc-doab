import logging
import requests

logger = logging.getLogger(__name__)


class BaseCorpusExtractor():
    def __init__(self, identifier):
        self.identifier = identifier

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.identifier}"

    @staticmethod
    def validate_identifier(identifier):
        """ Validates if this parser can handle the given identifier
        :return: `bool`
        """
        raise NotImplementedError()

    @classmethod
    def from_identifier(cls, identifier):
        if cls.validate_identifier(identifier):
            return cls(identifier)
        else:
            return None

    def extract(self):
        """ Returns an iterator of with the result from the extraction
        The items returned should be tuples with the structure
        (filename, data_blob)
        """
        raise NotImplementedError


class PDFCorpusExtractor(BaseCorpusExtractor):
    @staticmethod
    def validate_identifier(identifier):
        session = requests.session()
        content_type = session.head(identifier).headers.get("content-type")
        if content_type == "application/pdf":
            return True
        return False

    def extract(self):
        response = requests.get(self.identifier)
        if response.status_code == 200:
            yield ("book.pdf", response.content)
        else:
            raise response.raise_for_status()


CORPUS_EXTRACTORS = [
    PDFCorpusExtractor,
]
