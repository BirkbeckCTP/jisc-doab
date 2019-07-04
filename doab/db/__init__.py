from contextlib import ContextDecorator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import(
    scoped_session,
    sessionmaker,
)

_ENGINE = None
_SESSION = None

def get_dsn():
    return "postgres://%s:%s@%s/%s" % (
        os.getenv("DOAB_DB_USER", "root"),
        os.getenv("DOAB_DB_PASSWORD", "root"),
        os.getenv("DOAB_DB_HOST", "db"),
        os.getenv("DOAB_DB_NAME", "doab"),
    )

def start_engine(dsn):
    global _ENGINE
    global _SESSION
    if not _ENGINE:
        _ENGINE = create_engine(dsn, echo=True)
        _SESSION = scoped_session(sessionmaker(_ENGINE))

class get_session(ContextDecorator):
    def __init__(self, *args, dsn=None, **kwargs):
        if not _ENGINE:
            start_engine(dsn or get_dsn())

    def __enter__(self):
        return _SESSION()

    def __exit__(self, *exc):
        _SESSION.remove()
