import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jisc-doab",
    version="0.0.1",
    author="Mauro Sanchez",
    author_email="mauro.sanchez@openlibhums.org",
    description="A set of tools for the completion of the Open Metrics for "
                "Monographs Experiment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mauromsl/jisc-doab",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests",
        "sickle",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        # "License :: OSI Approved :: TBD",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "doab = doab.cli:run"
        ]
    }
)
