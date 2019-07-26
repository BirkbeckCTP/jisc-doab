from itertools import chain
import logging
import re

from sqlalchemy.orm.exc import NoResultFound

from doab import const
from doab.db import models, session_context

logger = logging.getLogger(__name__)


def match(reference):
    matches = []
    for matcher in MATCHERS:
        matches += matcher(reference)
    return matches


def match_by_doi(reference):
    matches = []

    if "doi" not in reference or reference["doi"] is None:
        return matches

    with session_context() as session:
        parses_matching = session.query(
                models.ParsedReference
            ).filter(
                models.ParsedReference.doi == reference["doi"],
            )
    return chain.from_iterable(p.reference.books for p in parses_matching)


def match_title_exact(reference):
    if "title" not in reference or reference["title"] is None:
        return []
    with session_context() as session:
        parses_matching = session.query(
            models.ParsedReference,
        ).filter(
            models.ParsedReference.title == reference["title"],
        )
    return chain.from_iterable(p.reference.books for p in parses_matching)



def match_fuzzy(reference):
    title = reference.get("title")
    authors = reference.get("author", "")
    if "title" not in reference or reference["title"] is None:
        return []

    # Fuzzy text search on title against db
    with session_context() as session:
        parses_matching = session.query(
            models.ParsedReference,
            models.ParsedReference.title.op('<->')(title),
        ).filter(
            models.ParsedReference.title.op("%%")(title),
        )

        #refine with autors
        matches = []
        for parse, distance in parses_matching:
            logger.debug(f"Match score {distance}: '{title} || {parse.title}'")
            if (
                distance >= const.MIN_TITLE_THRESHOLD
                or match_authors_fuzzy(authors, parse)
            ):
                matches.append(parse.reference.books)


        return chain.from_iterable(matches)

def match_authors_fuzzy(authors, parse):
    """Determines if the authors from a parse match the given authors

    Authors are parsed from a citation as a comma/space separated string.
    Since there is no effective way of splitting the author string into
    individual authors, we intersect a set containing the names in each author
    string and determine the match based on arbitrary similarity weight
    """
    if not (authors and parse.authors):
        return False

    matched_names = set()
    initials, names = _split_names_initials(authors)
    parse_initials, parse_names = _split_names_initials(parse.authors)

    matched_names |= (names | parse_names)

    # Add the initials of the remaining names to the sets containing initials
    parse_initials |= (parse_names - names)
    initials |= (names - parse_names)

    matched_names |= (initials | parse_initials)

    return len(matched_names)/len(names|initials)


def _split_names_initials(authors):
    author_names = set(re.compile(r'\w+').findall(authors))
    initials, names = set(), set()
    for word in author_names:
        names.add(word.lower()) if len(word) > 1 else initials.add(word.lower())
    return initials, names

MATCHERS = [
    match_by_doi,
    match_title_exact,
    match_fuzzy,
]
