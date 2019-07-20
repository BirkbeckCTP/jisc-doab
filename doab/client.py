"""
Python clients for iteracting with DOAB site and APIs
"""
import json
import logging
from urllib.parse import urlparse

from sickle import Sickle

from doab import const
from doab.corpus_extractors import CORPUS_EXTRACTORS

logger = logging.getLogger(__name__)


def record_is_active_book(record):
    return (
        record.header.deleted is False
        and "book" in record.metadata["type"]
    )

class DOABOAIClient():

    def __init__(self):
        self._sickle = Sickle(const.DOAB_OAI_ENDPOINT)

    def fetch_records_for_publisher_id(self, publisher_id):
        return self._fetch_records(publisher_id=publisher_id)

    def fetch_all_records(self):
        return self._fetch_records()

    def _fetch_records(self, publisher_id=None):
        kwargs = {
            "metadataPrefix": "oai_dc",
        }
        if publisher_id is not None:
            kwargs["set"] = f"publisher_{publisher_id}"

        return (
            DOABRecord(record)
            for record in self._sickle.ListRecords(**kwargs)
            if record_is_active_book(record)
        )


class DOABRecord():
    """ A wrapper for an OAI record extracted from DOAB """
    def __init__(self, record):
        self.metadata = record.metadata
        # identifier header format is 'oai:doab-books:{id}'
        self.doab_id = record.header.identifier.split(":")[-1]
        self.identifiers = filter(is_uri, record.metadata["identifier"])
        extractors = [
            extractor.from_identifier(self, identifier, self.metadata)
            for identifier in self.identifiers
            for extractor in CORPUS_EXTRACTORS
        ]
        self.extractors = [
            extractor
            for extractor in extractors
            if extractor is not None
        ]

    def __str__(self):
        return f"<{self.__class__.__name__}:{self.doab_id}>"

    def persist(self, writer):
        labels = []
        for extractor in self.extractors:
            for label, data in extractor.extract():
                writer.write_bytes(
                    self.doab_id,
                    filename=label,
                    to_write=data,
                )
                labels.append(label)
        print(f"Extracted {len(labels)} items: {labels}")


def is_uri(uri):
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc, result.path])
    except Exception as e:
        print(e)
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
