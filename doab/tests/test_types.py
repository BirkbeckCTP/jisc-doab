import sys

from doab.commands import db_populator, parse_references
from doab.const import DEFAULT_OUT_DIR
from doab.reference_matching import match


class TestManager(object):
    TEST_CASES = []

    @classmethod
    def register(cls, test_case):
        cls.TEST_CASES.append(test_case)

    @classmethod
    def test(cls):
        for Test in cls.TEST_CASES:
            test = Test()
            test.run()

    def __new__(*args, **kwargs):
        raise NotImplementedError


class AcceptanceTest(object):
    """ A Base class for running acceptance tests

    Children must declare a CITATION, BOOK_IDS and INPUT_PATH in order
    to run assert_references_matched
    implement `run()`
    """
    CITATION = ""
    BOOK_IDS = []
    INPUT_PATH = DEFAULT_OUT_DIR

    def __init__(self):
        db_populator(self.INPUT_PATH, self.BOOK_IDS)
        parse_references(self.INPUT_PATH, self.BOOK_IDS)

    def assert_references_matched(self):
        expected = {id_ for id_ in self.BOOK_IDS}
        books = match(self.CITATION)
        result = {book.doab_id for book in books}
        print(f"Expected book IDS: {self.BOOK_IDS}")
        print(f"Matched book IDS: {result}")
        failures = expected - result
        if failures:
            sys.stderr.write(f"[FAILED] Missed book ids: {failures}")
            sys.exit(1)
        else:
            sys.stdout.write("[SUCCESS]")

    def run(self):
        self.assert_references_matched()
