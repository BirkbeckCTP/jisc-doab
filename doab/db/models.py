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
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

book_author = Table("book_author", Base.metadata,
    Column("book_id", String, ForeignKey("book.doab_id")),
    Column("author_id", String, ForeignKey("author.standarised_name")),
    UniqueConstraint('book_id', 'author_id', name="unique_book_author"),
)


class Book(Base):
    __tablename__ = "book"
    doab_id = Column(String, primary_key=True)
    title = Column(String)
    publisher = Column(String)
    description = Column(Text)
    doi = Column(String)

    authors = relationship(
        "Author",
        secondary=book_author,
        backref="books",
    )
    identifiers = relationship("Identifier", backref="book")
    references = relationship("Reference", backref="referrer")

    def update_with_metadata(self, metadata):
        self.title = metadata["title"],
        self.description = metadata["description"]
        self.publisher = metadata["publisher"]


class Identifier(Base):
    __tablename__ = "identifier"
    value = Column(String, primary_key=True)
    book_id = Column(String, ForeignKey("book.doab_id"))


class Reference(Base):
    __tablename__ = "reference"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Text, ForeignKey("book.doab_id"))


class Author(Base):
    __tablename__ = "author"
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    standarised_name = Column(String, primary_key=True)
    reference_name = Column(String)