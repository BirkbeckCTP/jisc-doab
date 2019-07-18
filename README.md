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

## Command Line tools

The following command line tools are currently supported:

```
usage: doab [-h] [-d] {extract,publishers,populate,parse,match} ...

positional arguments:
  {extract,publishers,populate,parse,match}
                        commands
    extract             Tool for extraction of corpus and metadata from DOAB
    publishers          Prints a list of all the supported publishers
    populate            Populates the database with the metadata extracted
                        with `extract`
    parse               Parses the references for the provided book IDs
    match               Tries to match the given reference with a book

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Sets debug mode on
```


There is a magic publisher_id argument that will extract the entire DOAB repository:
`doab extract all`

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
