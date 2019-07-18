from itertools import chain

from sqlalchemy.orm.exc import NoResultFound

from doab.db import models, session_context


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
                models.ParsedReference.references.books
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

def match_title_fuzzy(reference):
    #TODO: Add weighting by match score
    if "title" not in reference or reference["title"] is None:
        return []
    title = reference["title"]
    match_term = f"%{title}%"
    with session_context() as session:
        parses_matching = session.query(
            models.ParsedReference,
        ).filter(
            models.ParsedReference.title.op("%%")(match_term),
        )
    return chain.from_iterable(p.reference.books for p in parses_matching)

MATCHERS = [
    match_by_doi,
    match_title_exact,
    match_title_fuzzy,
]