import logging
import os
import sys


from sqlalchemy.orm.exc import NoResultFound

from doab.files import FileManager
from doab.db import models

from .reference_finders import (
    BloomsburyReferenceFinder,
    CambridgeReferenceFinder,
    PDFDOIFinder,
    SpringerEPUBReferenceFinder,
    CitationTXTReferenceFinder,
)

from .reference_parsers import (
    AnystyleParser,
    CermineParser,
    CrossrefParser,
    BloomsburyAcademicParser,
    CambridgeCoreParser,
)

logger = logging.getLogger(__name__)


class ReferenceMiner(object):
    REFERENCE_PARSERS = []
    # magic value of 'all' will always return true
    PUBLISHER_NAMES = []

    def __init__(self, book_id, book_path):
        self.book_id = book_id
        self.book_path = book_path
        self.references = {}
        self.parsers = [parser() for parser in self.REFERENCE_PARSERS]
        self.finders = [
            finder(book_id, book_path)
            for finder in self.REFERENCE_FINDERS
        ]

    def run(self, session=None):
        self.prepare()
        self.parse()
        if session:
            self.persist(session)
        else:
            self.echo()

    def prepare(self):
        for finder in self.finders:
            for reference in finder.find():
                if reference not in self.references:
                    self.references[reference] = {}


    def parse(self):
        for reference in self.references.keys():
            for parser in self.parsers:
                parsed = parser.parse_reference(reference)
                self.references[reference][parser.NAME] = parsed

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
            session.commit()

            # Store parses of reference if they have a title
            for parser, parsed in parses.items():
                if parsed and "title" in parsed and parsed["title"]:
                    try:
                        parsed_reference = session.query(
                            models.ParsedReference
                        ).filter(
                            models.ParsedReference.reference_id==reference.id,
                            models.ParsedReference.parser==parser,
                        ).one()

                        logger.debug("Existing reference found. Ignoring. Use nuke command to update.")
                    except NoResultFound:
                        parsed_reference = models.ParsedReference(
                            reference_id=reference.id,
                            raw_reference=ref,
                            parser=parser,
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
                elif parsed:
                    logger.debug(f"{parser} returned None")
                else:
                    logger.debug(f"{parser} didn't parse a title: {parsed}")


    def echo(self, stream=None):
        """Prints parse results to the provided stream"""
        if stream is None:
            stream = sys.stdout
        for reference in self.references:
            print(reference, file=stream)

    @classmethod
    def can_handle(cls, book, input_path):
        if (
            'all' in cls.PUBLISHER_NAMES
            or book.publisher in cls.PUBLISHER_NAMES
        ):
            filetypes = FileManager(os.path.join(input_path, book.doab_id)).types

            for filetype in cls.FILE_TYPES:
                if filetype == 'all':
                    return True

                if filetype not in filetypes:
                    return False

            logger.debug(f'{cls} parser can handle {book.doab_id}')
            return True
        return False


class PalgraveMiner(ReferenceMiner):
    REFERENCE_PARSERS = [CermineParser, CrossrefParser]
    REFERENCE_FINDERS = [SpringerEPUBReferenceFinder]
    PUBLISHER_NAMES = ['{"Palgrave Macmillan"}']
    FILE_TYPES = ['epub']


class SpringerMiner(ReferenceMiner):
    REFERENCE_PARSERS = [CermineParser, CrossrefParser]
    REFERENCE_FINDERS = [SpringerEPUBReferenceFinder]
    PUBLISHER_NAMES = ['{Springer}']
    FILE_TYPES = ['epub']


class CambridgeCoreMiner(ReferenceMiner):
    # <meta name = "citation_reference" content = "citation_title=title; citation_author=author;
    # citation_publication_date=1990" >
    REFERENCE_PARSERS = [CambridgeCoreParser, CrossrefParser]
    REFERENCE_FINDERS = [CambridgeReferenceFinder]
    PUBLISHER_NAMES = ['{"Cambridge University Press"}']
    FILE_TYPES = ['CambridgeCore']


class PDFMiner(ReferenceMiner):
    REFERENCE_PARSERS = (CrossrefParser,)
    REFERENCE_FINDERS = (PDFDOIFinder,)
    FILE_TYPES = ["pdf"]
    PUBLISHER_NAMES = ["all"]


class BloomsburyAcademicMiner(ReferenceMiner):
    PUBLISHER_NAMES = ['{"Bloomsbury Academic"}']
    REFERENCE_PARSERS = [
        BloomsburyAcademicParser,
        CrossrefParser,
    ]
    REFERENCE_FINDERS = [BloomsburyReferenceFinder]
    FILE_TYPES = ['all']


class CitationTXTReferenceMiner(ReferenceMiner):
    PUBLISHER_NAMES = "all"
    REFERENCE_PARSERS = [AnystyleParser, CrossrefParser]
    REFERENCE_FINDERS = [CitationTXTReferenceFinder]
    FILE_TYPES = ["txt"]


PARSERS = [
    AnystyleParser,
    CermineParser,
    CrossrefParser,
    BloomsburyAcademicParser,
    CambridgeCoreParser,
    CitationTXTReferenceFinder,
]

FINDERS = [
    BloomsburyReferenceFinder,
    CambridgeReferenceFinder,
    SpringerEPUBReferenceFinder,
    CitationTXTReferenceFinder
]

MINERS = [
    PalgraveMiner,
    SpringerMiner,
    CambridgeCoreMiner,
    BloomsburyAcademicMiner,
    PDFMiner,
    CitationTXTReferenceMiner,
]
