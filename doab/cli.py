import argparse
import sys
from timeit import default_timer as timer

from doab import const
from doab.commands import (
    extractor,
    print_publishers,
    db_populator,
    parse_references,
    match_reference,
)
from doab.config import init_logging

#
## Const
#

# Commands
EXTRACT_CMD = "extract"
PUBLISHERS_CMD = "publishers"
POPULATOR_CMD = "populate"
PARSE_CMD = "parse"
MATCH_CMD = "match"

# Argument names
PUBLISHER_ID = "publisher_id"
OUTPUT_PATH = "output_path"
INPUT_PATH = "input_path"
BOOK_IDS = "book_ids"
REFERENCE = "citation"

# Arguments

BOOK_IDS_ARG = (
    ("-b", f"--{BOOK_IDS}"),
    {"help": "A list of book ids for which to populate their db records. "
        "If not provided, all books found in the input path will be processed ",
    "nargs": "+",
    "type": int,
    "dest": BOOK_IDS},
)

INPUT_PATH_ARG = (
    ("-i", f"--{INPUT_PATH}"),
    {"help": f"Path to the desired input directory, defaults to "
        "`pwd`/{const.DEFAULT_OUT_DIR}",
    "default": f"{const.DEFAULT_OUT_DIR}",
    "dest" : INPUT_PATH},
)

#
## Validators
#


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

def string_is_digit(arg):
    if not arg.is_digit():
        raise argparse.ArgumentTypeError(
            "'%s' is not a valid book id" % arg
        )
    return int(arg)


parser = argparse.ArgumentParser()
parser.add_argument(
    "-d", "--debug",
    help="Sets debug mode on",
    action="store_true",
    default=False,
)

subparsers = parser.add_subparsers(help="commands", dest="incantation")
#
## Extractor parser
#
extract_parser = subparsers.add_parser(
    EXTRACT_CMD,
    help="Tool for extraction of corpus and metadata from DOAB",
)
extract_parser.add_argument(
    f"{PUBLISHER_ID}",
    help="The identifier for the publisher in DOAB",
    type=publisher_validator
)
extract_parser.add_argument(
    "-o", f"--{OUTPUT_PATH}",
    help=f"Path to the desired ouput directory, defaults to "
        "`pwd`/{const.DEFAULT_OUT_DIR} ",
    default=f"{const.DEFAULT_OUT_DIR}",
)

#
## Publisher parser
#

publishers_parser = subparsers.add_parser(
    PUBLISHERS_CMD,
    help="Prints a list of all the supported publishers",
)

#
## DB Populator parser
#

populator_parser = subparsers.add_parser(
    POPULATOR_CMD,
    help="Populates the database with the metadata extracted with `extract`",
)
populator_parser.add_argument(*INPUT_PATH_ARG[0], **INPUT_PATH_ARG[1])
populator_parser.add_argument(*BOOK_IDS_ARG[0], **BOOK_IDS_ARG[1])


#
## Reference parsing parser
#
parse_parser = subparsers.add_parser(
    PARSE_CMD,
    help="Parses the references for the provided book IDs",
)
parse_parser.add_argument(*INPUT_PATH_ARG[0], **INPUT_PATH_ARG[1])
parse_parser.add_argument(*BOOK_IDS_ARG[0], **BOOK_IDS_ARG[1])

#
## Reference matching parser
#
match_parser = subparsers.add_parser(
    MATCH_CMD,
    help="Tries to match the given reference with a book",
)
match_parser.add_argument(*INPUT_PATH_ARG[0], **INPUT_PATH_ARG[1])
match_parser.add_argument(
    f"{REFERENCE}",
    help="A Citation to be matched against the local database",
)

COMMANDS_MAP = {
    EXTRACT_CMD: (
        extractor,
        (PUBLISHER_ID, OUTPUT_PATH),
    ),
    POPULATOR_CMD: (
        db_populator,
        (INPUT_PATH, BOOK_IDS),
    ),
    PARSE_CMD: (
        parse_references,
        (INPUT_PATH, BOOK_IDS),
    ),
     MATCH_CMD: (
        match_reference,
        (REFERENCE,),
     ),
       PUBLISHERS_CMD: (print_publishers, ""),
}


def run():
    args = parser.parse_args()
    init_logging(args.debug)

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
