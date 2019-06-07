import argparse

from doab.client import DOABOAIClient
from doab import const
from doab.files import FileManager

EXTRACT_CMD = "extract"
PUBLISHERS_CMD = "publishers"
PUBLISHER_ID = "publisher_id"


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help="commands", dest="incantation")

extract_parser = subparsers.add_parser(
    EXTRACT_CMD,
    help="Tool for extraction of corpus and metadata from DOAB",
)
extract_parser.add_argument(
    "publisher_id",
    help="The identifier for the publisher in DOAB",
    type=int
)

publishers_parser = subparsers.add_parser(
    PUBLISHERS_CMD,
    help="Prints a list of all the supported publishers",
)


def extract_corpus_for_publisher_id(publisher_id):
    writer = FileManager("out")
    client = DOABOAIClient()
    records = client.fetch_records_for_publisher_id(publisher_id)
    for record in records:
        print(f"Ectracting Corpus for DOAB record with ID {record.doab_id}")
        record.persist(writer)


def print_publishers():
    for pub in const.Publisher:
        print(f"{pub.value}\t{pub.name}")


COMMANDS_MAP = {
    EXTRACT_CMD: (extract_corpus_for_publisher_id, (PUBLISHER_ID,)),
    PUBLISHERS_CMD: (print_publishers, "")
}


def run():
    args = parser.parse_args()
    if args.incantation not in COMMANDS_MAP:
        parser.print_help()
    else:
        command, arg_names = COMMANDS_MAP[args.incantation]
        command(*(getattr(args, arg) for arg in arg_names))


if __name__ == "__main__":
    run()
