from doab.tests.test_types import AcceptanceTest, TestManager


@TestManager.register
class PalgraveAcceptanceTestA(AcceptanceTest):
    CITATION = "Foucault,  M.  (1991).  Discipline  and  Punish.  The  Birth  of  the  Prison  St.  Ives:  Penguin"
    BOOK_IDS = {"24596", "20716", "27401"} #24598


@TestManager.register
class PalgraveAcceptanceTestB(AcceptanceTest):
    CITATION = "Ackers, H. L., Ioannou, E., & Ackers-Johnson, J. (2016). The impact of delays on maternal and neonatal outcomes in Ugandan public health facilities: The role of absenteeism. Health Policy and Planning, 1–10. doi:10.1093/heapol/czw046."
    BOOK_IDS = {"21612", "20717", "21612"}


@TestManager.register
class PalgraveAcceptanceTestC(AcceptanceTest):
    CITATION = "Norton, D., & Marks-Maran, D. (2014). Developing cultural sensitivity and awareness in nursing overseas. Nursing Standard, 28(44), 39–43.CrossRef"
    BOOK_IDS = {"21610", "21612"}
