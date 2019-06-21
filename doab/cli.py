import argparse
import logging
import sys
from timeit import default_timer as timer

from doab.commands import extractor, print_publishers
EXTRACT_CMD = "extract"
PUBLISHERS_CMD = "publishers"
PUBLISHER_ID = "publisher_id"
OUTPUT_PATH = "output_path"


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

    elif arg.isdigit():
        arg = int(arg)
    else:
        raise argparse.ArgumentTypeError(
            "'%s' is not a valid publisher id" % arg
        )

    return arg


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
    type=publisher_validator
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


COMMANDS_MAP = {
    EXTRACT_CMD: (
        extractor,
        (PUBLISHER_ID, OUTPUT_PATH)
    ),
    PUBLISHERS_CMD: (print_publishers, "")
}


def run():
    args = parser.parse_args()
    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG)

    if args.incantation not in COMMANDS_MAP:
        parser.print_help()
    else:
        command, arg_names = COMMANDS_MAP[args.incantation]
        start = timer()
        command(*(getattr(args, arg) for arg in arg_names))
        end = timer()
        if args.debug:
            print(end - start)


def exit():
    print("Bye!")
    sys.exit(0)


if __name__ == "__main__":
    run()
