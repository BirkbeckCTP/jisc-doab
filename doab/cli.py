"""Jisc Open Monographs Metrics Experiment.

Usage:
  cli.py extract_texts [--output_path=PATH] [--publisher_id=ID] [--threads=THREAD] [options]
  cli.py import_metadata [--input_path=PATH] [--threads=THREAD] [--book_id=BOOK_IDS...] [options]
  cli.py parse_references [--input_path=PATH] [--threads=THREAD] [--book_id=BOOK_IDS...] [--dry-run] [options]
  cli.py match_reference <reference> [--parser=PARSER] [--input_path=PATH] [options]
  cli.py list_citations [--book_id=BOOK_IDS...] [options]
  cli.py list_books [--input_path=PATH] [options]
  cli.py list_publishers [options]
  cli.py list_parsers [options]
  cli.py nuke_citations [--book_id=BOOK_IDS...] [options]
  cli.py nuke_intersections [--book_id=BOOK_IDS...] [options]
  cli.py intersect [options] [-n --dry-run] [--book_id=BOOK_IDS...]
  cli.py list_intersections [options]
  cli.py list_references <book_id> [options]

  cli.py (-h | --help)
  cli.py --version

Options:
  -d --debug    Enable debug mode
  -y --yes      Answer with "y" any confirmation requests

"""
import sys

from doab import const
from docopt import docopt
from doab.config import init_logging
from pprint import pprint

from doab.commands import (
    db_populator,
    extractor,
    intersect,
    list_intersections,
    list_references,
    match_reference,
    nuke_citations,
    nuke_intersections,
    parse_references,
    print_books,
    print_parsers,
    print_citations,
    print_publishers,
)

CONFIRM = True

def run():
    args = docopt(__doc__, version='Jisc Open Monographs Metrics Experiment 1.0')
    init_logging(args['--debug'])
    if args["--yes"]:
        global CONFIRM
        CONFIRM = False

    # normalize arguments
    if not args['--output_path']:
        args['--output_path'] = const.DEFAULT_OUT_DIR

    if not args['--input_path']:
        args['--input_path'] = const.DEFAULT_OUT_DIR

    if not args['--threads']:
        args['--threads'] = 0
    else:
        args['--threads'] = int(args['--threads'])

    if not args['--publisher_id']:
        args['--publisher_id'] = 'all'

    if not args['--parser']:
        args['--parser'] = 'Cermine'

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
        parse_references(
            args['--input_path'],
            args['--book_id'],
            args['--threads'],
            args['--dry-run'],
        )
    elif args['match_reference']:
        match_reference(args['<reference>'], args['--parser'])
    elif args['list_parsers']:
        print_parsers()
    elif args['list_citations']:
        print_citations(args['--book_id'])
    elif args['nuke_intersections']:
        nuke_intersections()
    elif args['nuke_citations']:
        nuke_citations(args['--book_id'])
    elif args['intersect']:
        intersect(dry_run=args["--dry-run"], book_ids=args["--book_id"])
    elif args['list_intersections']:
        list_intersections()
    elif args["list_references"]:
        pprint(list_references(args["<book_id>"]))


def publisher_validator(arg):
    """ Ensures that the publisher id argument is either an int or 'all' """
    if arg == "all" and CONFIRM:
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
