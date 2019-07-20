"""
DOAB related constants
"""
from enum import Enum
import os

DOAB_URL = "https://www.doabooks.org"
DOAB_OAI_ENDPOINT = DOAB_URL + "/oai"

DEFAULT_OUT_DIR = os.getenv("DOAB_DEFAULT_OUT_DIR", "volumes/out")

RECOGNIZED_BOOK_TYPES = {'epub': 'book.epub',
                         'pdf': 'book.pdf',
                         'CambridgeCore': 'cc.html'}

class Publisher(Enum):
    CAMBRIDGE_UNIVERSITY_PRESS = 1244
    OXFORD_UNIVERSITY_PRESS = 1210
    PALGRAVE_MACMILLAN = 1112
