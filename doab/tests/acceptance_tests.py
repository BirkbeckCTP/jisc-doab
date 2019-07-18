from doab.tests.test_types import AcceptanceTest, TestManager


@TestManager.register
class PalgraveAcceptanceTest(AcceptanceTest):
    CITATION = "Foucault,  M.  (1991).  Discipline  and  Punish.  The  Birth  of  the  Prison  St.  Ives:  Penguin"
    BOOK_IDS = {"24596"}
