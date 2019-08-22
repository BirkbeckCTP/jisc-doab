# jisc-doab

This repository contains a set of tools and utilities for the completion of the Open Metrics for Monographs experiment by the Birkbeck Centre for Technology and Publishing


## Installation Instructions

This project requires python 3.7+

After cloning the repository, install the dependencies with pip:
`pip install -t requirements.txt`

Then, the project can be installed with:
`pip install .`

To install the project only for your current user only run:
`pip install --user .`

To install the project in development mode run
`pip install -e .`


When reference parsing, this project relies on a few third-party tools that are expected to be available
on your system path:

`anystyle` (forked): available at https://github.com/mauromsl/anystyle-cli
`cermine` v1.3: available at https://github.com/CeON/CERMINE/releases

Parse results are stored in a postgres backend, used by the intersection tool to match references.
Installation instructions available at: https://www.postgresql.org/docs/9.3/tutorial-install.html

The following docker image is prepackaged with all the third party dependancies installed:
https://hub.docker.com/r/birkbeckctp/doab-base
(See docker installation instructions below)

## Command Line tools

The following command line tools are currently supported:

```
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
```


There is a magic `publisher_id` argument 'all' that will extract the entire DOAB repository.

### Running the CL within a docker container
If you don't want to install the doab tools onto your system, you can also run them within a docker container.
The included docker-compose file will run a postgres service to be used by the CLI tools

GNU Make commands are available for the most common operations:

```
help:		 Show this help.
doab-cli:	 Run DOAB commands in a container, the command should passed through the CMD variable (e.g.: `make doab-cli CMD="publishers")
install:	 Runs database migrations on the postgres database
rebuild:	 Rebuild the doab docker image.
shell:		 Starts an interactive shell within a docker container build from the same image as the one used by the CLI
db-client:	 Runs the database CLI client interactively within the database container
uninstall:	 Removes all DOAB related docker containers, docker images and database volumes
check:		 Runs the test suite
```
