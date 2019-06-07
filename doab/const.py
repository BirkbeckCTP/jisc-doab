"""
DOAB related constants
"""
from enum import Enum

DOAB_URL = "https://www.doabooks.org"
DOAB_OAI_ENDPOINT = DOAB_URL + "/oai"


class Publisher(Enum):
    CAMBRIDGE_UNIVERSITY_PRESS = 1244
    OXFORD_UNIVERSITY_PRESS = 1210
