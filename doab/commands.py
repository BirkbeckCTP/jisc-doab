from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import chain, islice
import json
import logging
import os

from sqlalchemy.orm.exc import NoResultFound
from unidecode import unidecode

from doab import const
from doab.client import DOABOAIClient
from doab.db import models, session_context, get_session, get_engine
from doab.files import FileManager
from doab.reference_matching import match
from doab import reference_parsers
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

                print(book.citation(input_path))

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


def nuke_citations(book_ids=None):
    with session_context() as session:
        if not book_ids:
            books = session.query(models.Book).all()
            for book in books:
                try:
                    for reference in book.references:
                        for parsed_ref in reference.parsed_references:
                            session.delete(parsed_ref)
                        session.delete(reference)

                    session.commit()
                    print(f'Nuked references for book {book.doab_id}')
                except NoResultFound:
                    logger.error(f'Error retrieving book {book.doab_id}.')
        else:

            for book_id in book_ids:
                # fetch book metadata
                try:
                    book = session.query(
                        models.Book
                    ).filter(models.Book.doab_id == str(book_id)).one()

                    for reference in book.references:
                        for parsed_ref in reference.parsed_references:
                            session.delete(parsed_ref)
                        session.delete(reference)

                    session.commit()
                    print(f'Nuked references for book {book.doab_id}')
                except NoResultFound:
                    logger.error(f'Error retrieving book {book_id}.')


def print_citations(book_ids=None):
    with session_context() as session:
        for book_id in book_ids:
            # fetch book metadata
            try:
                book = session.query(
                    models.Book
                ).filter(models.Book.doab_id == str(book_id)).one()

                for reference in book.references:
                    print(reference)

            except NoResultFound:
                logger.error(f'Error retrieving book {book_id}.')

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
                ).filter(models.Book.doab_id == str(book_id)).one()

                parsers = book.parsers(input_path)

                if parsers:
                    for parser in parsers:
                        logger.debug("Running parser {0} for book {1}.".format(parser, book_id))
                        parser_for_book = parser(book_id, path)
                        parser_for_book.run(session)
                else:
                    logger.debug(f'No appropriate parser found for {book_id}.')

            except NoResultFound:
                logger.error(f'Error retrieving book {book_id}.')

        except FileNotFoundError as e:
            logger.debug(f"No book.epub available: {e}")


def match_reference(reference=None, parser='Cermine'):
    parser_class = reference_parsers.get_parser_by_name(parser)

    clean = parser_class.clean(reference)
    parsed_reference = parser_class.parse_reference(clean)

    with session_context() as session:
        matches = {book.doab_id: book for book in match(parsed_reference, session)}
        print(f"Matched {len(matches)} books referencing the same citation")
        for i, matched in enumerate(matches.values(), 1):
            print (f"{i}. {matched.doab_id} - {matched.title}")
        return matches


def print_parsers():
    print('Single citation parsers:')
    for parser in reference_parsers.MIXIN_PARSERS:
        print(parser.PARSER_NAME)


def intersect(publisher_id=None, workers=0):
    with session_context() as session:
        ref_ids = session.query(
            models.Reference.id
        ).filter(
            models.Reference.matched_id == None
        ).all()
    msg = "Matching References"
    # Not thread safe yet
    results = tasker.run(intersect_reference, ref_ids, msg, 0)


def intersect_reference(reference_id):
    """Intersects all the parses of the reference with the entire DB

    First we fetch all the different parses for this reference, then we `match`
    them and put all the matches with the original reference onto an intersection
    """
    references_matched = set()
    intersection = None

    with session_context() as session:
        parses = session.query(
            models.ParsedReference
        ).filter(
            models.ParsedReference.reference_id == reference_id,
        )
        for parse in parses:
            logger.debug(f"Matching with {parse.parser} parser")
            references_matched |= set(
                match(parse, session, return_references=True)
            )

        logger.debug("")
        references = session.query(
            models.Reference,
        ).filter(
            models.Reference.id.in_(references_matched)
        )
        for ref in references:
            # If any of the references is in an intersection
            # then all the new matches should be in the same one
            intersection = ref.intersection

        if not intersection:
            # If None of the matches is an intersection yet, create one
            intersection = models.Intersection()
            session.add(intersection)

        intersection.references.extend(references.all())
        session.commit()


def next_n(n, iterable):
    """ Returns the next N items from iterable """
    return list(islice(iterable, n))


def chunk_iterable(n, iterable, keys = None):
    """ Returns an iterator that yields a list of the next n items

    :param int n: The number of items per chunk
    :param iterable: The iterable to be chunked:
    :param tuple keys: The keys to be zipped with each chunk
    """
    new_iterable = partial(next_n, n, iter(iterable))
    if keys:
        return iter(zip(keys, new_iterable), [])
    else:
        return iter(new_iterable, [])


class ListIntersections():
    QUERY = """
    SELECT
        i.id,
        count(r.id) AS intersected_ref_ids,
        string_agg(r.id, '|') AS ref_ids,
        count(b.book_id) AS intersected_book_ids,
        string_agg(b.book_id, '|') AS book_ids
    FROM public.intersection i
    JOIN public.reference r ON r.matched_id = i.id
    JOIN public.book_reference b ON b.reference_id = r.id
    GROUP  BY i.id
    HAVING count(b.book_id) > 1
    ORDER BY count(b.book_id) desc;
    """
    CHUNK_SIZE = 10

    def __init__(self, session, chunk_size=CHUNK_SIZE):
        engine = get_engine()
        self._resultset = engine.execute(self.QUERY)
        self._iterable = chunk_iterable(
            chunk_size,
            self._resultset,
        )

    def __iter__(self):
        return self._iterable

def list_intersections():
    with session_context() as session:
        intersection_chunks = ListIntersections(session)
        idx = 0
        for chunk in intersection_chunks:
            for id, ref_count, ref_ids, book_count, book_ids in chunk:

                idx += 1
                ref_ids = ref_ids.split("|")
                print(f"{idx}. {book_count} books across {ref_count} "
                      f"matched references.\n - book ids: {book_ids} ")

                try:
                    for ref_id in ref_ids:
                        ref = session.query(
                            models.Reference
                        ).filter(models.Reference.id == ref_id).one()
                        print(f"{ref}")
                except:
                    pass
                finally:
                    pass

                #print(f"{idx}. {book_count} books across {ref_count} "
                #      f"matched references.\n - book ids: {book_ids} "
                #      f"\n - Matched References: \n\t - {ref_ids}")
            #input("Press Enter to continue...")
