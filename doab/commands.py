from concurrent.futures import ThreadPoolExecutor
from itertools import chain
import json
import logging
import os

from sqlalchemy.orm.exc import NoResultFound
from unidecode import unidecode

from doab import const
from doab.client import DOABOAIClient
from doab.db import models, session_context
from doab.files import FileManager
from doab.reference_matching import match
from doab.reference_parsers import (
    CermineParserMixin,
    PalgraveEPUBParser,
    CrossrefParserMixin)
from doab import tasker

logger = logging.getLogger(__name__)


def print_publishers():
    for pub in const.Publisher:
        print(f"{pub.value}\t{pub.name}")


def print_books(input_path):
    with session_context() as session:
        for book_id in list_extracted_books(input_path):
            try:
                book = session.query(
                    models.Book
                ).filter(models.Book.doab_id == book_id).one()

                print(book.citation)

            except NoResultFound:
                print('Book with ID: {0}'.format(book_id))


def list_extracted_books(path):
    file_manager = FileManager(path)
    return file_manager.list()


def extractor(publisher_id, output_path, workers=0):
    executor = ThreadPoolExecutor(max_workers=workers or 1)
    writer = FileManager(output_path)
    client = DOABOAIClient()
    if publisher_id == "all":
        records = client.fetch_all_records()
    else:
        records = client.fetch_records_for_publisher_id(publisher_id)
    for record in records:
        print(f"Extracting Corpus for DOAB record with ID {record.doab_id}")
        if workers:
            executor.submit(record.persist, writer)
        else:
            record.persist(writer)


def db_populator(input_path, book_ids=None, workers=0):
    if not book_ids:
        book_ids = list_extracted_books(input_path)
    reader = FileManager(input_path)
    msg = "Populating DB records for book "
    tasker.run(populate_db, book_ids, msg, workers, reader)


def populate_db(book_id, reader):
        try:
            raw_metadata = reader.read(str(book_id), "metadata.json")
        except FileNotFoundError as e:
            logger.error(e)
            return
        metadata = json.loads(raw_metadata)
        upsert_book(book_id, metadata)


def upsert_book(book_id, metadata):
    book_id = str(book_id)
    with session_context() as session:
        try:
            book = session.query(
                models.Book
            ).filter(models.Book.doab_id == book_id).one()
        except NoResultFound:
            book = models.Book(doab_id=book_id)
            session.add(book)

        book.update_with_metadata(metadata)
        for author_str in metadata["creator"]:
            author = upsert_author(session, author_str)
            book.authors.append(author)
        for identifier_str in metadata["identifier"]:
            identifier = upsert_identifier(session, identifier_str)
            identifier.book = book
        session.commit()


def upsert_author(session, author_str):
    """ Updates/Inserts authors to the database from the doab creator string

    :param author: A doab formatterdauthor string ("last names, names")
    """
    standarised, first, middle, last, reference = process_author_str(author_str)
    try:
        author = session.query(
            models.Author
        ).filter(models.Author.standarised_name == standarised).one()
    except NoResultFound:
        author = models.Author(standarised_name=standarised)
    author.first_name = first
    author.middle_name = middle
    author.last_name = last
    author.reference = reference

    return author


def process_author_str(author):
    """Breaks author string into all its relevant parts

    :param author: A doab formatterdauthor string ("last names, names")
    :return: standarised, first_name, middle_name, last_name, reference_name
    """
    transliterated = unidecode(author)
    try:
        # Surname, names
        last_name, names = transliterated.split(",")
    except ValueError:
        # Names Surname
        names, last_name = transliterated.rsplit(" ", 1)
    standarised_name = " ".join((names, last_name))
    first_name, *middle_names = names.split()
    middle_name = " ".join(middle_names)
    reference_name = "" #TODO

    return standarised_name, first_name, middle_name, last_name, reference_name


def upsert_identifier(session, identifier_str):
    """ Updates/Inserts an identifier from its DOAB identifier string

    :param identifier: string
    """
    try:
        identifier = session.query(
            models.Identifier
        ).filter(models.Identifier.value == identifier_str).one()
    except NoResultFound:
        identifier = models.Identifier(value=identifier_str)
    return identifier


def parse_references(input_path, book_ids=None, workers=0):
    if not book_ids:
        book_ids = list_extracted_books(input_path)
    msg = "Parsing book"
    tasker.run(parse_reference, book_ids, msg, workers, input_path)


def parse_reference(book_id, input_path):
    path = os.path.join(input_path, str(book_id))
    with session_context() as session:
        try:
            # fetch book metadata
            try:
                book = session.query(
                    models.Book
                ).filter(models.Book.doab_id == book_id).one()

                for parser in book.parsers:
                    parser_for_book = parser(book_id, path)
                    parser.run(session)

            except NoResultFound:
                publisher = None

            # match publisher to parser
            if publisher:
                pass
            else:
                logger.debug(f"No publisher info for {0} so unable to match to parser.".format(book_id))

        except FileNotFoundError as e:
            logger.debug(f"No book.epub available: {e}")


def match_reference(reference=None):
    # TODO: Allow user to choose parser?
    clean = CermineParserMixin.clean(reference)
    parsed_reference = CermineParserMixin.parse_reference(clean)
    matches = {(book.doab_id, book.title) for book in match(parsed_reference)}
    print(f"Matched {len(matches)} books referencing the same citation")
    for i, matched in enumerate(matches, 1):
        book_id, title = matched
        print (f"{i}. {book_id} - {title}")
    return matches
