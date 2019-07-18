from doab.tests.test_types import AcceptanceTest, TestManager


@TestManager.register
class BrokenTest(AcceptanceTest):
    CITATION = "banana"
    BOOK_IDS = {"1", "2", "3"}
