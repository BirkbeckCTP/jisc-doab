import logging
import json
import re
import requests
from bs4 import BeautifulSoup

from doab import const
from doab.concurrency import get_http_session

logger = logging.getLogger(__name__)


class BaseExtractor():

    allow_multiple = True
    IDENTIFIER = 'BaseExtractor'

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
    IDENTIFIER = 'BaseCorpusExtractor'

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


class HTTPCorpusExtractorMixin(BaseCorpusExtractor):
    """ A Mixin that adds adds a session based HTTP client """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = get_http_session()

    def _fetch(self, uri):
        response = self._session.get(uri)
        if response.ok:
            return(response.content)
        else:
            response.raise_for_status()


class MimeBasedCorpusExtractor(BaseCorpusExtractor):
    IDENTIFIER = 'MimeBasedCorpusExtractor'
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
    IDENTIFIER = 'JSONMetadataExtractor'
    METADATA_KEYS = {
        "title", "identifier", "creator",
        "language", "publisher", "date",
        "description",
    }

    @classmethod
    def validate_identifier(cls, identifier, doab_record):
        return identifier.startswith(
            "https://www.doabooks.org/doab?func=search")

    @classmethod
    def get_doi_from_metadata(cls, metadata):
        """ Matches a DOI in the metadata by re.findall
        :param metadata: A `Mapping` from metadata keys to metadata values
        :return: A DOI `str` or `None`
        """
        if not metadata["description"]:
            return None

        description = "\n".join(metadata["description"])
        matches  = re.findall(const.DOI_RE, description)
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
    IDENTIFIER = 'PDFCorpusExtractor'
    CONTENT_TYPE = "application/pdf"
    FILE_LABEL = const.RECOGNIZED_BOOK_TYPES['pdf']


class EPUBCorpusExtractor(MimeBasedCorpusExtractor):
    IDENTIFIER = 'EPUBCorpusExtractor'
    CONTENT_TYPE = "application/epub+zip"
    FILE_LABEL = const.RECOGNIZED_BOOK_TYPES['epub']


class DebugCorpusExtractor(BaseCorpusExtractor):
    IDENTIFIER = 'DebugCorpusExtractor'
    @staticmethod
    def validate_identifier(identifier, metadata):
        session = requests.session()
        content_type = session.head(identifier).headers.get("content-type")
        print("[IDENTIFIER] -  ", identifier)
        print("[CONTENT_TYPE] - ", content_type)
        return False


class BloomsburyExtractor(HTTPCorpusExtractorMixin, BaseCorpusExtractor):
    """ Extracts formatted HTML from Bloomsbury Academic
    """

    allow_multiple = False

    IDENTIFIER = 'BloomsburyExtractor'
    PUBLISHER_NAME = 'Bloomsbury Academic'
    HTML_BASE_URL = 'https://www.bloomsburycollections.com'
    DOI = ''

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return doab_record.metadata['publisher'][0] == BloomsburyExtractor.PUBLISHER_NAME

    def extract(self):
        from doab.client import is_uri
        identifiers = filter(is_uri, self.record.metadata['identifier'])

        first_run = True

        for identifier in identifiers:
            try:
                base = self._fetch(identifier)
                soup = BeautifulSoup(base, "html.parser")
                new_regex = '(\/book\/BOOK_TITLE_HERE/.+)'
                chapter_title_regex = '/book/BOOK_TITLE_HERE/(.+)'
                title_regex = re.compile(r'\/book\/(.+?).ris')

                for ref in soup.find_all(name='a', attrs={'href': lambda x : x.startswith('/book/') if x else None}):
                    if first_run:
                        title = title_regex.search(ref['href']).group(1)
                        new_regex = new_regex.replace('BOOK_TITLE_HERE', title)
                        chapter_title_regex = chapter_title_regex.replace('BOOK_TITLE_HERE', title)
                        first_run = False

                for ref in soup.find_all(name='a', href=re.compile(new_regex)):
                    if ref and 'href' in ref.attrs and '{page_no}' not in ref['href']:
                        yield (f'{re.search(chapter_title_regex, ref["href"]).group(1)}.html',
                               self._fetch(f'{self.HTML_BASE_URL}{ref["href"]}'))

            except requests.exceptions.HTTPError as e:
                first_run = True
                if e.response.status_code == 404:
                    logger.debug(f'Error fetching {self.PUBLISHER_NAME} URL')
                else:
                    logger.error(e)

    @property
    def doi(self):
        # DOIs are the last part of the identifier (suffix/prefix)
        return self.doi


class CambridgeUniversityPressExtractor(
    HTTPCorpusExtractorMixin, BaseCorpusExtractor
):
    """ Extracts formatted HTML from CUP

    Formatted HTML base:
        https://doi.org/10.1017/CBO<ISBN-13>
    """
    allow_multiple = False

    IDENTIFIER = 'CambridgeUniversityPressExtractor'
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
    IDENTIFIER = 'SpringerCorpusExtractor'

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return "springer.com" in identifier

    def extract(self):
        try:
            uri = f"{self.PDF_BASE_URL}{self.doi}.pdf"
            yield(const.RECOGNIZED_BOOK_TYPES['pdf'], self._fetch(uri))
        except requests.exceptions.HTTPError as e:
            # Some chapters are flagged as books leading to these
            # requests returning a 404
            if e.response.status_code == 404:
                logger.debug(e)
            else:
                logger.error(e)

        try:
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


class UPExtractor(BaseCorpusExtractor):

    def validate_identifier(identifier, doab_record):
        return False

CORPUS_EXTRACTORS = [
    #DebugCorpusExtractor,
    JSONMetadataExtractor,
    PDFCorpusExtractor,
    EPUBCorpusExtractor,
    SpringerCorpusExtractor,
    CambridgeUniversityPressExtractor,
    BloomsburyExtractor,
    UPExtractor,
]


def is_isbn(identifier):
    return True if identifier.startswith('ISBN:') else False
