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
        print(f"[{metadata.doab_id}:PUB] - {metadata.metadata['publisher']}")
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
    TITLE_TEMPL = '(\/book\/{book_title}/.+)'
    CHAPTER_TEMPL = '/book/{book_title}/(.+)'
    TITLE_RE = re.compile(r'\/book\/(.+?).ris')

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return doab_record.metadata['publisher'][0] == BloomsburyExtractor.PUBLISHER_NAME

    def extract(self):
        from doab.client import is_uri
        identifiers = filter(is_uri, self.record.metadata['identifier'])

        for identifier in identifiers:
            try:
                base = self._fetch(identifier)
                soup = BeautifulSoup(base, "html.parser")
                book_link = soup.find(name='a', attrs={'href':self.TITLE_RE})
                if not book_link:
                    logger.debug(f"Title slug not found in {identifier}")
                    continue
                title = self.TITLE_RE.search(book_link['href']).group(1)
                logger.debug(f"Found title slug {title}")
                search_re = self.TITLE_TEMPL.format(book_title=title)
                chapter_title_re = self.CHAPTER_TEMPL.format(book_title=title)

                for ref in soup.find_all(name='a', href=re.compile(search_re)):
                    if ref and 'href' in ref.attrs and '{page_no}' not in ref['href']:
                        yield (f'{re.search(chapter_title_re, ref["href"]).group(1)}.html',
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


class OpenEditionsExtractor(HTTPCorpusExtractorMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.oe_id = None
        self.publisher_url = None

    @staticmethod
    def validate_identifier(identifier, doab_record):
        return "openedition.org" in identifier

    def extract(self):
        self.publisher_url, self.oe_id, book_path = self.parse_landing_page()
        citations = self.traverse_reader(book_path)
        if citations:
            data = "\n".join(citations).encode("utf-8")
            yield(const.RECOGNIZED_BOOK_TYPES['txt'], data)
        else:
            logger.warning("{self} extracted no citations")
            return []


    def parse_landing_page(self):
        """Fetch and parse the landing page to find the link to the e-reader

        Soup looks like :
            <a class="inline-block" href="{book_path}">
                <span class="img available" id="acces-lire"></span>Some text
            </a>

        :return str: The URL for this publisher
        :return int: The OpenEditions ID for this book
        :return int: The path to the e-reader page for this book
        """
        #http://books.openedition.org/{publisher_code}/{book_id}
        publisher_url, oe_id = self.identifier.rsplit("/", 1)

        landing_page_html = self._fetch(self.identifier)
        soup = BeautifulSoup(landing_page_html, "html.parser")
        open_access = soup.find(name="span", attrs={"id":"acces-lire"})
        if not open_access:
            raise Exception("Book is not Open Access")
        book_path = open_access.parent["href"]

        return publisher_url, int(oe_id), int(book_path)


    def traverse_reader(self, book_path):
        """ Traverses all the pages in the reader looking for citations

        All the reader url paths in OpenEditions are numeric. To visit
        the next page we just increase the path by one.
        :return set: A set with all the citations found in the book
        """
        reader_url = f"{self.publisher_url}/{book_path}"
        citations = set()
        next_page_url = reader_url
        while next_page_url:
            soup = BeautifulSoup(self._fetch(next_page_url), "html.parser")
            logger.debug(f"Extracting citations from {next_page_url}")
            next_page_url, citations_in_page = self.extract_citations(
                soup, next_page_url)
            if citations_in_page:
                logger.debug(f"Extracted {len(citations_in_page)}")
                citations |= citations_in_page

        return citations


    def extract_citations(self, soup, page_url):
        """ Extracts the references available on the given page

        Open editions reader marks up the citations in one of two ways:
            - With the CSS class `bibliographie` on <p> tags
            - Within <p> tags in a div that contains an element with the CSS
                class `doi_pres`
        There is also a custom view where the reader makes ajax requests
            whose response contains all the citations for a given page
        :return str: The URL for the next page (if there is one)
        :retrun set(str): A set with all the extracted citations
        """
        citations = self.extract_from_citations_view(page_url)
        #citations |= self.extract_citations_with_css_tag(soup)
        #citations |= self.extract_citations_by_doi_div(soup)
        next_page_tag = soup.find(name="link", attrs={"rel": "Next"})
        if next_page_tag:
            next_page_url = next_page_tag["href"]
        else:
            next_page_url = None

        return next_page_url, citations

    def extract_from_citations_view(self, page_url):
        """Exctracts the citations from the view used by the book reader"""
        citation_querystring = "?format=bibliographie&lang=en&norecordurl=1"
        citations_url = f"{page_url}{citation_querystring}"
        soup = BeautifulSoup(self._fetch(citations_url), "html.parser")
        found = soup.find_all(name="p", attrs={
            "class": lambda class_: class_ in ("bibliographie", "texte")})
        if found:
            return {citation.text for citation in found}
        else:
            return set()


    @staticmethod
    def extract_citations_with_css_tag(soup):
        found = soup.find_all(name="p", attrs={"class": "bibliographie"})
        if found:
            return {citation.text for citation in found}
        else:
            return set()

    def extract_citations_by_doi_div(soup):
        has_citations = soup.find(name="div", attrs={"class": "doi_pres"})
        if has_citations:
            found = has_citations.parent.find_all(
                "p", attrs={"class", "texte"})
            if found:
                return {citation.text for citation in found}
        return set()


class UPExtractor(BaseCorpusExtractor):

    def validate_identifier(identifier, doab_record):
        return False


class OpenEditionsProber(DebugCorpusExtractor):
    IDENTIFIER = 'OpenEditionsProber'

    @classmethod
    def validate_identifier(cls, identifier, metadata):
        if "openedition.org" in identifier:
            super().validate_identifier(identifier, metadata)
        return False


CORPUS_EXTRACTORS = [
    #DebugCorpusExtractor,
    #OpenEditionsProber,
    OpenEditionsExtractor,
    JSONMetadataExtractor,
    PDFCorpusExtractor,
    EPUBCorpusExtractor,
    SpringerCorpusExtractor,
    CambridgeUniversityPressExtractor,
    BloomsburyExtractor,
    #UPExtractor,
]


def is_isbn(identifier):
    return True if identifier.startswith('ISBN:') else False
