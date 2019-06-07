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

Extract:

`doab extract`
```
usage: doab extract [-h] [-o OUTPUT_PATH] publisher_id

positional arguments:
  publisher_id          The identifier for the publisher in DOAB

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_PATH, --output_path OUTPUT_PATH
                        Path to the desired ouput directory, defaults to
                        `pwd`/out
```

There is a magic publisher_id argument that will extract the entire DOAB repository:
`doab extract all`
