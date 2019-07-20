import logging
import json
import re
import requests
from doab import const

logger = logging.getLogger(__name__)


class BaseExtractor():
    """ A Base class for extracting content"""
    def __init__(self, record, identifier):
        self.record = record
        self.identifier = identifier
        logger.debug(f"Preparing extractor {self}")

    @classmethod
    def from_identifier(cls, record, identifier, doab_record):
        """Instantiates the extractor if relevant for the identifier
        :param record: An instance of client.DOABRecord
        :return: an instance of `cls`
        """
        return cls(record, identifier)


class BaseCorpusExtractor(BaseExtractor):

    def __init__(self, record, identifier):
        super().__init__(record, identifier)

    def __str__(self):
        return f"{self.__class__.__name__}({self.identifier})"

    @staticmethod
    def validate_identifier(identifier, doab_record):
        """ Validates if this parser can handle the given identifier
        :return: `bool`
        """
        raise NotImplementedError()

    @classmethod
    def from_identifier(cls, record, identifier, metadata):
        if cls.validate_identifier(identifier, record):
            return super().from_identifier(record, identifier, record)
        else:
            return None

    def extract(self):
        """ Returns an iterator of with the result from the extraction
        The items returned should be tuples with the structure
        (filename, data_blob)
        """
        raise NotImplementedError

class MimeBasedCorpusExtractor(BaseCorpusExtractor):
    CONTENT_TYPE = None
    FILE_LABEL = None

    @classmethod
    def validate_identifier(cls, identifier, doab_record):
        session = requests.session()
        content_type = session.head(identifier).headers.get("content-type")
        if content_type == cls.CONTENT_TYPE:
            return True
        return False

    def extract(self):
        response = requests.get(self.identifier)
        if response.status_code == 200:
            yield (self.FILE_LABEL, response.content)
        else:
            raise response.raise_for_status()


class JSONMetadataExtractor(BaseCorpusExtractor):
    METADATA_KEYS = {
        "title", "identifier", "creator",
        "language", "publisher", "date",
        "description",
    }
    DOI_RE = re.compile(r"/^10.\d{4,9}/[-._;()/:A-Z0-9]+$/i")

    @classmethod
    def validate_identifier(cls, identifier, doab_record):
        return identifier.startswith("https://www.doabooks.org/doab?func=search")

    @classmethod
    def get_doi_from_metadata(cls, metadata):
        """ Matches a DOI in the metadata by re.findall
        :param metadata: A `Mapping` from metadata keys to metadata values
        :return: A DOI `str` or `None`
        """
        description = "\n".join(metadata["description"])
        matches  = re.findall(cls.DOI_RE, description)
        if not matches:
            doi = None
        elif len(matches) == 1:
           doi = matches[0]
        else:
            logger.debug(f"Matched more than one DOI {matches}")
            doi = matches[0]

        return doi

    def extract(self):
        metadata = {
            key: self.record.metadata.get(key)
            for key in self.METADATA_KEYS
        }
        json_string = json.dumps(metadata)
        metadata["DOI"] = self.get_doi_from_metadata(metadata)
        yield ("metadata.json", json_string.encode("utf-8"))


class PDFCorpusExtractor(MimeBasedCorpusExtractor):
    CONTENT_TYPE = "application/pdf"
    FILE_LABEL = const.RECOGNIZED_BOOK_TYPES['pdf']


class EPUBCorpusExtractor(MimeBasedCorpusExtractor):
    CONTENT_TYPE = "application/epub+zip"
    FILE_LABEL = const.RECOGNIZED_BOOK_TYPES['epub']


class DebugCorpusExtractor(BaseCorpusExtractor):
    @staticmethod
    def validate_identifier(identifier, metadata):
        session = requests.session()
        content_type = session.head(identifier).headers.get("content-type")
        print("[IDENTIFIER] -  ", identifier)
        print("[CONTENT_TYPE] - ", content_type)
        return False


class CambridgeUniversityPressExtractor(BaseCorpusExtractor):
    """ Extracts formatted HTML from CUP

    Formatted HTML base:
        https://doi.org/10.1017/CBO<ISBN-13>
    """

    PUBLISHER_NAME = 'Cambridge University Press'
    HTML_BASE_URL = 'https://doi.org/10.1017/CBO'

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return doab_record.metadata['publisher'][0] == CambridgeUniversityPressExtractor.PUBLISHER_NAME

    def extract(self):
        identifiers = filter(is_isbn, self.record.metadata['identifier'])
        for identifier in identifiers:
            isbn = identifier.split(':')[1].strip()
            try:
                uri = f"{self.HTML_BASE_URL}{isbn}"
                yield (const.RECOGNIZED_BOOK_TYPES['CambridgeCore'], self._fetch(uri))
            except requests.exceptions.HTTPError as e:
                # 404 here indicates that we are using the wrong ISBN and it's just trial and error
                if e.response.status_code == 404:
                    logger.debug('No Cambridge Core URL for ISBN {0}'.format(isbn))
                else:
                    logger.error(e)

    @staticmethod
    def _fetch(uri):
        response = requests.get(uri)
        if response.status_code == 200:
            return(response.content)
        else:
            response.raise_for_status()

    @property
    def doi(self):
        # DOIs are the last part of the identifier (suffix/prefix)
        return "/".join(self.identifier.split("/")[-2:])

class SpringerCorpusExtractor(BaseCorpusExtractor):
    """ Extracts PDF and EPUB book files

    Identifier:
        https://link.springer.com/book/<DOI>
    EPUB links:
        https://link.springer.com/download/epub/<DOI>.epub
    PDF links:
        https://link.springer.com/content/pdf/<DOI>.pdf
    """
    PDF_BASE_URL = "https://link.springer.com/content/pdf/"
    EPUB_BASE_URL = "https://link.springer.com/download/epub/"

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return "springer.com" in identifier

    def extract(self):
        try:
            uri = f"{self.PDF_BASE_URL}{self.doi}.pdf"
            yield(const.RECOGNIZED_BOOK_TYPES['pdf'], self._fetch(uri))
            uri = f"{self.EPUB_BASE_URL}{self.doi}.epub"
            yield(const.RECOGNIZED_BOOK_TYPES['epub'], self._fetch(uri))
        except requests.exceptions.HTTPError as e:
            # Some chapters are flagged as books leading to these
            # requests returning a 404
            if e.response.status_code == 404:
                logger.debug(e)
            else:
                logger.error(e)

    @staticmethod
    def _fetch(uri):
        response = requests.get(uri)
        if response.status_code == 200:
            return(response.content)
        else:
            response.raise_for_status()

    @property
    def doi(self):
        # DOIs are the last part of the identifier (suffix/prefix)
        return "/".join(self.identifier.split("/")[-2:])


CORPUS_EXTRACTORS = [
    #DebugCorpusExtractor,
    JSONMetadataExtractor,
    PDFCorpusExtractor,
    EPUBCorpusExtractor,
    SpringerCorpusExtractor,
    CambridgeUniversityPressExtractor,
]


def is_isbn(identifier):
    return True if identifier.startswith('ISBN:') else False
