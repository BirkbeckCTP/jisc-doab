from doab.tests.test_types import IntersectAcceptanceTest, TestManager, ReferenceParsingTest
from doab.parsing.reference_miners import (
    BloomsburyAcademicMiner,
    CambridgeCoreParser,
    CitationTXTReferenceMiner,
    SpringerMiner,
)

@TestManager.register
class PalgraveCUPIntersect(IntersectAcceptanceTest):
    CITATION = "C.P. Snow. 1993. The Two Cultures"
    BOOK_IDS = {"16498", "27401"}

@TestManager.register
class PalgraveAcceptanceTestA(IntersectAcceptanceTest):
    CITATION = "Foucault,  M.  (1991).  Discipline  and  Punish.  The  Birth  of  the  Prison  St.  Ives:  Penguin"
    BOOK_IDS = {"24596", "20716", "27401"} #24598


@TestManager.register
class PalgraveAcceptanceTestB(IntersectAcceptanceTest):
    CITATION = "Ackers, H. L., Ioannou, E., & Ackers-Johnson, J. (2016). The impact of delays on maternal and neonatal outcomes in Ugandan public health facilities: The role of absenteeism. Health Policy and Planning, 1–10. doi:10.1093/heapol/czw046."
    BOOK_IDS = {"21612", "20717", "21612"}


@TestManager.register
class PalgraveAcceptanceTestC(IntersectAcceptanceTest):
    CITATION = "Norton, D., & Marks-Maran, D. (2014). Developing cultural sensitivity and awareness in nursing overseas. Nursing Standard, 28(44), 39–43.CrossRef"
    BOOK_IDS = {"21610", "21612"}


@TestManager.register
class OpenEditionsTestA(IntersectAcceptanceTest):
    CITATION = "Durand Gilbert, Les Structures anthropologiques de l'imaginaire, Paris, Bordas, 1969."
    BOOK_IDS = {"16988", "19329", "20818", "20855", "20862", "20941", "21060", "21251", "22074", "22229", "22264"}


@TestManager.register
class OpenEditionsTestB(IntersectAcceptanceTest):
    CITATION = "Foucault M. (1975), Surveiller et punir, Paris, Gallimard."
    BOOK_IDS = {"9337", "20851", "21101", "21176", "21251"}


@TestManager.register
class OpenEditionsTestC(IntersectAcceptanceTest):
    CITATION = "Brynen Rex 1995,  The Neopatrimonial Dimension of Palestinian Politics , Journal of Palestine Studies 1, p. 23-36."
    BOOK_IDS = {"15809", "15815", "16571", "16583", "16604"}


class CEDEJParsingTest(ReferenceParsingTest):
    PUBLISHER_NAME = "CEDEJ"
    BOOK_REFERENCE_COUNTS = {
        "22138": 43,
        "22141": 51,
        "22142": 127,
        "22143": 103,
        "22213": 102,
    }
    MINER = CitationTXTReferenceMiner


class PalgraveParsingTest(ReferenceParsingTest):
    PUBLISHER_NAME = "Palgrave Macmillan"
    BOOK_REFERENCE_COUNTS = {
        "26919": 957,
        "27363": 387, 
        "27364": 157,
        "27401": 209,
        "27402": 398,
    }
    MINER = SpringerMiner


class BloomsburyParsingTest(ReferenceParsingTest):
    PUBLISHER_NAME = "Bloomsbury Academic"
    BOOK_REFERENCE_COUNTS = {
        "14368": 94,
        "15449": 145,
        "14372": 15,
        "14373": 211,
        "14376": 32,
    }
    MINER = BloomsburyAcademicMiner


class CasaVelazquezParsingTest(ReferenceParsingTest):
    PUBLISHER_NAME = "Casa de Velazquez"
    BOOK_REFERENCE_COUNTS = {
        "22583": 431,
        "22584": 84,
        "22585": 531,
        "22586": 495,
        "22587": 453,
    }
    MINER = CitationTXTReferenceMiner


class CambridgeCoreParsingTest(ReferenceParsingTest):
    PUBLISHER_NAME = "Cambridge University Press"
    BOOK_REFERENCE_COUNTS = {
        "15986": 0,
        "15989": 0,
        "16001": 0,
        "16498": 0,
        "21821": 0,
    }
    MINER = CambridgeCoreParser
