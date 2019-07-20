import re
from itertools import chain
import logging
import os
import shutil
import subprocess

from bs4 import BeautifulSoup
from bibtexparser.bparser import BibTexParser
from sqlalchemy.orm.exc import NoResultFound
import requests

from doab.files import EPUBFileManager
from doab.db import models, session_context

logger = logging.getLogger(__name__)


class BaseReferenceParser(object):
    """ A base class for implementing reference parsers

    The entrypoint for the parser is `parser.run()`
    ChildrenMustImplement
        prepare()
        parse_reference()
    The state is preserved under self.references which is a mapping from a
    reference string to a list of parsing results
    :param book_path: (str) The path to the book to be parsed
    """
    def __init__(self, book_id, book_path, *args, **kwargs):
        self.book_path = book_path
        self.book_id = str(book_id)
        self.references = {}

    def __str__(self):
        return f"<test>"

    def prepare(self):
        """ Routines to be run in preparation to parsing the references

        Should populate the self.references map
        """
        raise NotImplementedError

    def parse(self):
        """ The logic for parsing the references

        It reads self.references and adds a tuple of (parser, result)
        to each entry. When overriding, always call super(), as single parser
        may want to implement behaviour from multiple parsers(which is why this
        abstract method doesn't raise NotImplementedError)
        """
        pass

    @classmethod
    def parse_reference(cls, reference):
        return None

    def persist(self, session):
        """ Persists parse results to the database

        :param session: A SQLAlchemy session
        """
        book = session.query(
            models.Book
        ).filter(models.Book.doab_id == self.book_id).one()
        for ref, parses in self.references.items():
            # Link reference with book
            try:
                reference = session.query(
                    models.Reference
                ).filter(models.Reference.id == ref).one()
            except NoResultFound:
                reference = models.Reference(id=ref)
                session.add(reference)
            if reference not in book.references:
                book.references.append(reference)

            # Store parsed reference
            for parse in parses:
                if not parse:
                    logger.debug(f"Reference {ref} has not been parsed")
                    session.commit()
                    continue
                parser_type, parsed = parse
                try:
                    parsed_reference = session.query(
                        models.ParsedReference
                    ).filter(
                        models.ParsedReference.reference_id==reference.id,
                        models.ParsedReference.parser==parser_type,
                    ).one()
                    logger.debug("parsed reference found, ignoring...")
                except NoResultFound:
                    parsed_reference = models.ParsedReference(
                        reference_id=reference.id,
                        raw_reference=ref,
                        parser=parser_type,
                        authors=parsed.get("author"),
                        title=parsed.get("title"),
                        pages=parsed.get("pages"),
                        journal=parsed.get("journal"),
                        volume=parsed.get("volume"),
                        doi=parsed.get("doi"),
                        year=parsed.get("year"),
                    )
                    session.add(parsed_reference)
                session.commit()

    def echo(self):
        """Prints parse results to stdout"""
        for reference in self.references:
            print(reference)

    def run(self, session=None):
        self.prepare()
        self.parse()
        if session:
            self.persist(session)
        else:
            self.echo()

    @staticmethod
    def clean(reference):
        logger.debug(f"Cleaning {reference}")
        without_newlines = reference.replace("\u200b", "").replace("\n", " ")
        without_redundant_space = " ".join(without_newlines.split())
        return without_redundant_space


class SubprocessParserMixin(BaseReferenceParser):
    """ Mixin for calling an external routine in a subprocess"""
    CMD = ""

    def __init__(self, *args, **kwargs):
        self.check_cmd()
        super().__init__(*args, **kwargs)

    def check_cmd(self):
        if not shutil.which(self.CMD):
            raise EnvironmentError(f"command `{self.CMD}` not in path")

    @classmethod
    def call_cmd(cls, *args):
        stdout = subprocess.check_output([cls.CMD, *args])
        return stdout.decode("utf-8")


class HTTPBasedParserMixin(BaseReferenceParser):
    """ Mixin for requesting references to be parsed by an HTTP service"""
    REQ_METHOD = ""
    SVC_URL = ""

    def call_svc(self, params=None, data=None):
        svc_caller = getattr(requests, self.REQ_METHOD)
        response = svc_caller()
        return response


class EPUBPrepareMixin(BaseReferenceParser):
    HTML_FILTER = (None, None)

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        self.file_manager = EPUBFileManager(os.path.join(book_path, "book.epub"))

    def prepare(self):
        for _, content in self.file_manager.read(mime="application/xhtml+xml"):
            soup = BeautifulSoup(content, "html.parser")
            self.process_soup(soup)

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        for ref in soup.find_all(name=tag, attrs=attributes):
            clean = self.clean(ref.text)
            self.references[clean] = []


class CrossrefParserMixin(HTTPBasedParserMixin):
    """A parser that matches DOIS and retrieves metadata via Crossref API"""

    def prepare(self):
        pass

    def parse(self):
        # using the Crossref approved single DOI: https://www.crossref.org/blog/dois-and-matching-regular-expressions/
        # 'for the 74.9M DOIs we have seen this matches 74.4M of them'
        crossref_doi_re = re.compile(r'/^10.\d{4,9}/[-._;()/:A-Z0-9]+$/i')
        for ref, parse in self.references.items():
            crossref_match = crossref_doi_re.search(ref)
            if crossref_match:
                logger.debug(crossref_match)

    @classmethod
    def parse_reference(cls, reference, bibtex_parser=None):
        if bibtex_parser is None:
            bibtex_parser = BibTexParser()
        #bibtex_reference = cls.call_cmd(*chain(cls.ARGS, (reference,)))
        #logger.debug(f"Bibtex {bibtex_reference}")
        #return bibtex_parser.parse(bibtex_reference).get_entry_list()[-1]
        return None


class CermineParserMixin(SubprocessParserMixin):
    CMD = "cermine"
    ARGS = [
        "pl.edu.icm.cermine.bibref.CRFBibReferenceParser",
        "-format", 'bibtex', "-reference",
    ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bibtex_parser = BibTexParser()

    def parse(self):
        for raw_ref in self.references.keys():
            logger.debug(f"Parsing {raw_ref}")
            result = self.parse_reference(raw_ref, self.bibtex_parser)
            self.references[raw_ref].append((self.CMD, result))

    @classmethod
    def parse_reference(cls, reference, bibtex_parser=None):
        if bibtex_parser is None:
            bibtex_parser = BibTexParser()
        bibtex_reference = cls.call_cmd(*chain(cls.ARGS, (reference,)))
        logger.debug(f"Bibtex {bibtex_reference}")
        return bibtex_parser.parse(bibtex_reference).get_entry_list()[-1]


class PublisherSpecificMixin(object):
    # magic value of 'all' will always return true
    PUBLISHER_NAMES = []
    FILE_TYPES = []

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)

    @classmethod
    def can_handle(cls, book, input_path):
        if 'all' in cls.PUBLISHER_NAMES:
            return True

        if book.publisher in cls.PUBLISHER_NAMES:
            if 'epub' in cls.FILE_TYPES:
                return EPUBFileManager(os.path.join(input_path, book.doab_id, "book.epub")).is_epub
            else:
                return True
        else:
            return False


class PalgraveEPUBParser(CermineParserMixin, EPUBPrepareMixin, PublisherSpecificMixin):
    HTML_FILTER = ("div", {"class": "CitationContent"})
    PUBLISHER_NAMES = ['{"Palgrave Macmillan"}']
    FILE_TYPES = ['epub']


def yield_parsers(book, input_path):
    parsers = []
    for parser in PARSERS:
        if parser.can_handle(book, input_path):
            parsers.append(parser)
    return parsers


PARSERS = [PalgraveEPUBParser]