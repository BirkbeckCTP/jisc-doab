from concurrent.futures import ThreadPoolExecutor
from itertools import chain
import json
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
)


def print_publishers():
    for pub in const.Publisher:
        print(f"{pub.value}\t{pub.name}")


def extractor(publisher_id, output_path, multithread=False):
    executor = ThreadPoolExecutor(max_workers=15)
    writer = FileManager(output_path)
    client = DOABOAIClient()
    if publisher_id == "all":
        records = client.fetch_all_records()
    else:
        records = client.fetch_records_for_publisher_id(publisher_id)
    for record in records:
        print(f"Extracting Corpus for DOAB record with ID {record.doab_id}")
        if multithread:
            executor.submit(record.persist, writer)
        else:
            record.persist(writer)


def db_populator(input_path, book_ids=None, multithreaded=False):
    reader = FileManager(input_path)
    executor = ThreadPoolExecutor(max_workers=15)
    for book_id in book_ids:
        raw_metadata = reader.read(str(book_id), "metadata.json")
        metadata = json.loads(raw_metadata)
        if multithreaded:
            executor.submit(upsert_book, book_id, metadata)
        else:
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

def parse_references(input_path, book_ids=None, multithreaded=False):
    with session_context() as session:
        for book_id in book_ids:
            path = os.path.join(input_path, str(book_id))
            parser = PalgraveEPUBParser(book_id, path) #TODO map publisher to parser
            parser.run(session)

def match_reference(reference=None):
    # TODO: Allow user to choose parser?
    clean = CermineParserMixin.clean(reference)
    parsed_reference = CermineParserMixin.parse_reference(clean)
    matches = match(parsed_reference)
    print(f"Matched {len(matches)} books referencing the same citation")
    for i, matched in enumerate(matches, 1):
       print (f"{i}. {matched.doab_id} - {matched.title}") 
    return matches