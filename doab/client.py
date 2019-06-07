"""
Python clients for iteracting with DOAB site and APIs
"""
import logging
from urllib.parse import urlparse

from sickle import Sickle

import const
from corpus_extractors import CORPUS_EXTRACTORS


class DOABOAIClient():

    def __init__(self):
        self._sickle = Sickle(const.DOAB_OAI_ENDPOINT)

    def fetch_records_for_publisher_id(self, publisher_id):
        records = self._sickle.ListRecords(
            metadataPrefix='oai_dc',
            set=f"publisher_{publisher_id}",
        )
        return (
            DOABRecord(record)
            for record in records
            if record.header.deleted is False
        )


class DOABRecord():
    """ A wrapper for an OAI record extracted from DOAB """

    def __init__(self, record):
        self.metadata = record.metadata
        # identifier header format is 'oai:doab-books:{id}'
        self.doab_id = record.header.identifier.split(":")[-1]
        self.identifiers = filter(is_uri, record.metadata["identifier"])
        parsers = [
            parser.from_identifier(identifier)
            for identifier in self.identifiers
            for parser in CORPUS_EXTRACTORS
        ]
        self.parsers = [parser for parser in parsers if parser is not None]

    def __str__(self):
        return f"<{self.__class__.__name__}:{self.publisher_id}>"

    def persist(self, writer):
        for parser in self.parsers:
            for label, data in parser.parse():
                yield label
                writer.write(
                    self.doab_id,
                    filename=label,
                    to_write=data,
                )


def is_uri(uri):
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc, result.path])
    except Exception as e:
        print(e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
