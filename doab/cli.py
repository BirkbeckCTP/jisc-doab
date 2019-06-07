import argparse
import logging
import sys

from doab.client import DOABOAIClient
from doab import const
from doab.files import FileManager

EXTRACT_CMD = "extract"
PUBLISHERS_CMD = "publishers"
PUBLISHER_ID = "publisher_id"
OUTPUT_PATH = "output_path"


parser = argparse.ArgumentParser()
parser.add_argument(
    "-d", "--debug",
    help="Sets debug mode on",
    action="store_true",
    default=False,
)

subparsers = parser.add_subparsers(help="commands", dest="incantation")

extract_parser = subparsers.add_parser(
    EXTRACT_CMD,
    help="Tool for extraction of corpus and metadata from DOAB",
)
extract_parser.add_argument(
    "publisher_id",
    help="The identifier for the publisher in DOAB",
    type=str
)
extract_parser.add_argument(
    "-o", "--output_path",
    help="Path to the desired ouput directory, defaults to `pwd`/out ",
    default="out",
)

publishers_parser = subparsers.add_parser(
    PUBLISHERS_CMD,
    help="Prints a list of all the supported publishers",
)


def extract_corpus_for_publisher_id(publisher_id, output_path):
    writer = FileManager(output_path)
    client = DOABOAIClient()
    if publisher_id == "all":
        records = client.fetch_all_records()
    else:
        records = client.fetch_records_for_publisher_id(publisher_id)
    for record in records:
        print(f"Ectracting Corpus for DOAB record with ID {record.doab_id}")
        record.persist(writer)


def print_publishers():
    for pub in const.Publisher:
        print(f"{pub.value}\t{pub.name}")


COMMANDS_MAP = {
    EXTRACT_CMD: (
        extract_corpus_for_publisher_id,
        (PUBLISHER_ID, OUTPUT_PATH)
    ),
    PUBLISHERS_CMD: (print_publishers, "")
}


def publisher_validator(arg):
    """ Ensures that the publihser id argument is either an int or 'all' """
    if arg == "all":
        response = ""
        while response.lower() not in {"y", "n"}:
            response = input(
                "WARNING! You are requesting to extract the entire DOAB "
                "database. Proceed? [y/N]: "
            )
        if response.lower() == "n":
            exit()

    elif arg.is_digit():
        arg = int(arg)
    else:
        raise TypeError("'%s' is not a valid publisher id")

    return arg


def run():
    args = parser.parse_args()
    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG)

    if args.incantation not in COMMANDS_MAP:
        parser.print_help()
    else:
        command, arg_names = COMMANDS_MAP[args.incantation]
        command(*(getattr(args, arg) for arg in arg_names))


def exit():
    print("Bye!")
    sys.exit(0)


if __name__ == "__main__":
    run()
