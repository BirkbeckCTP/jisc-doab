"""
ORM models for the persistence of DOAB metadata objects
"""
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

book_author = Table("book_author", Base.metadata,
    Column("book_id", Integer, ForeignKey("book.doab_id")),
    Column("author_id", String, ForeignKey("author.id")),
)

class Book(Base):
    doab_id = Column(String)
    title = Column(String)
    publisher = Column(String)
    description = Column(Text)

    authors = relationship(
        "Author",
        secondary=book_author,
        backref="books",
    )
    identifiers = relationship("Identifier", backref="book")


class Identifier(Base):
    value = Column(String)


class Author(Base):
    id = Column(String)
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)