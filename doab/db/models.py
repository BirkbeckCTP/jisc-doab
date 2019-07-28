"""
ORM models for the persistence of DOAB metadata objects
"""
from uuid import uuid4

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from doab import const
from doab.files import EPUBFileManager
from doab.reference_parsers import yield_parsers, get_parser_by_name

Base = declarative_base()

#Linking table: Authors of a book
book_author = Table("book_author", Base.metadata,
    Column("book_id", String, ForeignKey("book.doab_id")),
    Column("author_id", String, ForeignKey("author.standarised_name")),
    UniqueConstraint('book_id', 'author_id', name="unique_book_author"),
)

#Linking table, references contained in a booj
book_reference = Table("book_reference", Base.metadata,
    Column("book_id", String, ForeignKey("book.doab_id")),
    Column("reference_id", String, ForeignKey("reference.id")),
    UniqueConstraint('book_id', 'reference_id', name="unique_book_reference"),
)


class Book(Base):
    __tablename__ = "book"
    __table_args__ = (
        Index('title_idx', "title",
              postgresql_ops={"title": "gin_trgm_ops"},
              postgresql_using='gin'),
    )

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
    references = relationship(
        "Reference",
        secondary=book_reference,
        lazy='dynamic',
        backref="books",
    )

    identifiers = relationship("Identifier", backref="book")
    intersection = relationship("Intersection", backref="book", uselist=False)

    def parsers(self, input_path=const.DEFAULT_OUT_DIR):
        return yield_parsers(self, input_path)

    def citation(self, input_path=const.DEFAULT_OUT_DIR):
        output = ''
        for author in self.authors:
            output += '{0}{1}{2} {3}, '.format(author.first_name,
                                               ' ' if author.middle_name and author.middle_name != '' else '',
                                               author.middle_name, author.last_name)
        output += self.title
        output += ' ({0}). Handled by: {1}. ID: {2}'.format(self.publisher, self.parsers(input_path), self.doab_id)

        return output

    def update_with_metadata(self, metadata):
        self.title = metadata["title"],
        self.description = metadata["description"]
        self.publisher = metadata["publisher"]


class Identifier(Base):
    __tablename__ = "identifier"
    value = Column(String, primary_key=True)
    book_id = Column(String, ForeignKey("book.doab_id"))


class Reference(Base):
    def __str__(self):
        if len(self.parsed_references) > 0:
            # find the parser with the greatest accuracy
            prs = list(self.parsed_references)
            prs.sort(reverse=True, key=lambda x: get_parser_by_name(x.parser, mixin_only=False).accuracy)

            return str(prs[0])
        else:
            return ''

    __tablename__ = "reference"
    id = Column(String, primary_key=True)
    matched_id = Column(Text, ForeignKey("intersection.id"), nullable=True)


    parsed_references = relationship("ParsedReference", backref="reference", lazy="joined")


class ParsedReference(Base):
    def __str__(self):
        out = {'authors': self.authors,
               'title': self.title,
               'journal': self.journal,
               'volume': self.volume,
               'doi': self.doi,
               'year': self.year,
               'parser': self.parser}

        # add the raw reference if this is a bad parse
        if self.title == '' or self.authors == '':
            out['raw'] = self.raw_reference

        return str(out)

    __tablename__ = "parsed_reference"
    __table_args__ = (
        Index('parse_ref_title_idx', "title",
              postgresql_ops={"title": "gin_trgm_ops"},
              postgresql_using='gin'),
    )
    reference_id = Column(String, ForeignKey("reference.id"), primary_key=True)
    raw_reference = Column(Text)
    parser = Column(String, primary_key=True)
    authors = Column(String, nullable=True)
    title = Column(String, nullable=True)
    pages = Column(String, nullable=True)
    journal = Column(String, nullable=True)
    volume = Column(String, nullable=True)
    doi = Column(String, nullable=True)
    year = Column(String, nullable=True)


class Author(Base):
    __tablename__ = "author"
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    standarised_name = Column(String, primary_key=True)
    reference_name = Column(String)


def generate_uuid():
    return str(uuid4())


class Intersection(Base):
    __tablename__ = "intersection"
    id = Column(String, primary_key=True, default=generate_uuid)
    book_id = Column(String, ForeignKey("book.doab_id"), nullable=True)
    references = relationship("Reference", backref="intersection")
