from doab.tests.test_types import AcceptanceTest, TestManager

@TestManager.register
class PalgraveCUPIntersect(AcceptanceTest):
    CITATION = "C.P. Snow. 1993. The Two Cultures"
    BOOK_IDS = {"16498", "27401"}

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


@TestManager.register
class class OpenEditionsTestA(AcceptanceTest):
    CITATION = "Durand Gilbert, Les Structures anthropologiques de l'imaginaire, Paris, Bordas, 1969."
    BOOK_IDS = {"16988", "19329", "20818", "20855", "20862", "20941", "21060", "21251", "22074", "22229", "22264"}


@TestManager.register
class OpenEditionsTestB(AcceptanceTest):
    CITATION = "Foucault M. (1975), Surveiller et punir, Paris, Gallimard."
    BOOK_IDS = {"9337", "20851", "21101", "21176", "21251"}


@TestManager.register
class OpenEditionsTestC(AcceptanceTest):
    CITATION = "Brynen Rex 1995,  The Neopatrimonial Dimension of Palestinian Politics , Journal of Palestine Studies 1, p. 23-36."
    BOOK_IDS = {"15809", "15815", "16571", "16583", "16604"}
