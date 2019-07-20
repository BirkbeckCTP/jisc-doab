"""Jisc Open Monographs Metrics Experiment.

Usage:
  cli.py extract_texts [--output_path=PATH] [--publisher_id=ID] [--threads=THREAD] [options]
  cli.py import_metadata [--input_path=PATH] [--threads=THREAD] [--book_id=BOOK_IDS...] [options]
  cli.py parse_references [--input_path=PATH] [--threads=THREAD] [--book_id=BOOK_IDS...] [options]
  cli.py match_reference <reference> [--input_path=PATH] [options]
  cli.py list_books [--input_path=PATH] [options]
  cli.py list_publishers [options]
  cli.py list_parsers [options]

  cli.py (-h | --help)
  cli.py --version

Options:
  -d --debug    Enable debug mode

"""
import sys

from doab import const
from docopt import docopt
from doab.config import init_logging

from doab.commands import (
    extractor,
    print_publishers,
    db_populator,
    parse_references,
    match_reference,
    print_books,
    print_parsers
)


def run():
    args = docopt(__doc__, version='Jisc Open Monographs Metrics Experiment 1.0')
    init_logging(args['--debug'])

    # normalize arguments
    if not args['--output_path']:
        args['--output_path'] = const.DEFAULT_OUT_DIR

    if not args['--input_path']:
        args['--input_path'] = const.DEFAULT_OUT_DIR

    if not args['--threads']:
        args['--threads'] = 0

    if not args['--publisher_id']:
        args['--publisher_id'] = 'all'

    # select the action
    if args['extract_texts']:
        publisher_validator(args['--publisher_id'])
        extractor(args['--publisher_id'], args['--output_path'], args['--threads'])
    elif args['list_publishers']:
        print_publishers()
    elif args['list_books']:
        print_books(args['--input_path'])
    elif args['import_metadata']:
        db_populator(args['--input_path'], args['--book_id'], args['--threads'])
    elif args['parse_references']:
        parse_references(args['--input_path'], args['--book_id'], args['--threads'])
    elif args['match_reference']:
        match_reference(args['<reference>'])
    elif args['list_parsers']:
        print_parsers()


def publisher_validator(arg):
    """ Ensures that the publisher id argument is either an int or 'all' """
    if arg == "all":
        response = ""
        while response.lower() not in {"y", "n"}:
            response = input(
                "WARNING! You are requesting to extract the entire DOAB "
                "database. Proceed? [y/N]: "
            )
        if response.lower() == "n":
            sys.exit(0)

    elif arg.isdigit():
        arg = int(arg)
    else:
        print("'%s' is not a valid publisher id" % arg)

    return arg


if __name__ == '__main__':
    run()
