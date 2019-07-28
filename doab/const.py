"""
DOAB related constants
"""
from enum import Enum
import os
import re
from crossref.restful import Etiquette

# Search weights
MIN_TITLE_THRESHOLD = 0.25
MIN_AUTHOR_THRESHOLD = 1/2

CROSSREF_ETIQUETTE = Etiquette('Jisc DOAB Experiment', 'v1.0', 'https://www.jisc.ac.uk/rd/projects/open-metrics-lab',
                               'martin@eve.gd')


DOAB_URL = "https://www.doabooks.org"
DOAB_OAI_ENDPOINT = DOAB_URL + "/oai"

DOI_RE = re.compile(r"10.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)

DEFAULT_OUT_DIR = os.getenv("DOAB_DEFAULT_OUT_DIR", "volumes/out")

RECOGNIZED_BOOK_TYPES = {
    'epub': 'book.epub',
    'pdf': 'book.pdf',
    'CambridgeCore': 'cc.html',
}


class Publisher(Enum):
    CAMBRIDGE_UNIVERSITY_PRESS = 1244
    OXFORD_UNIVERSITY_PRESS = 1210
    PALGRAVE_MACMILLAN = 1112
    BLOOMSBURY_ACADEMIC = 1131
