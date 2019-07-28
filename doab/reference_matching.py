from itertools import chain
import logging
import re
from functools import singledispatch

from sqlalchemy.orm.exc import NoResultFound

from doab import const
from doab.db import models, session_context

logger = logging.getLogger(__name__)


@singledispatch
def match(reference, session, return_references=False):
    matches = []
    for matcher in MATCHERS:
        matched = matcher(reference, session)
        if return_references:
            matches += matched.keys()
        else:
            matches += chain.from_iterable(matched.values())
    return matches

@match.register(models.ParsedReference)
def match_parsed_reference(reference, *args, **kwargs):
    d = {
        "title": reference.title,
        "doi": reference.doi,
        "author": reference.authors,
    }
    return match(d, *args, **kwargs)


def match_by_doi(reference, session):
    if "doi" not in reference or reference["doi"] is None:
        return {}

    parses_matching = session.query(
            models.ParsedReference
        ).filter(
            models.ParsedReference.doi == reference["doi"],
        )
    return {p.reference_id: p.reference.books for p in parses_matching}



def match_title_exact(reference, session):
    if "title" not in reference or reference["title"] is None:
        return {}
    parses_matching = session.query(
        models.ParsedReference,
    ).filter(
        models.ParsedReference.title == reference["title"],
    )
    return {p.reference_id: p.reference.books for p in parses_matching}


def match_fuzzy(reference, session):
    title = reference.get("title")
    authors = reference.get("author", "")
    if "title" not in reference or reference["title"] is None:
        return {}

    # Fuzzy text search on title against db
    title = reference["title"]
    match_term = f"%{title}%"
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
            (distance <= const.MIN_TITLE_THRESHOLD)
            or match_authors_fuzzy(authors, parse)
        ):
            matches.append(parse)


    return {p.reference_id: p.reference.books for p in matches}

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

    matched_names &= (names & parse_names)

    # Add the initials of the remaining names to the sets containing initials
    parse_initials &= (parse_names - names)
    initials &= (names - parse_names)

    matched_names &= (initials & parse_initials)
    logger.debug(f"Matched names: {matched_names}")

    try:
        return (
            len(matched_names)/len(names|initials)
            >= const.MIN_AUTHOR_THRESHOLD
        )
    except ZeroDivisionError:
        return False

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
