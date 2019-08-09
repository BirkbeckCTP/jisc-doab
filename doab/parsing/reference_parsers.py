import json
from itertools import chain
import logging
import shutil
import subprocess
import re

from bibtexparser.bparser import BibTexParser
from bs4 import BeautifulSoup
from crossref.restful import Works
import requests

from doab import const

logger = logging.getLogger(__name__)


class BaseReferenceParser(object):
    """ A base class for implementing reference parsers

    ChildrenMustImplement
        parse_reference()
    :param book_path: (str) The path to the book to be parsed
    """
    # a variable that children can override to specify how good they are
    # compared to other parsers
    accuracy = 0

    @classmethod
    def parse_reference(cls, reference):
        return None

    @staticmethod
    def clean(reference):
        logger.debug(f"Cleaning {reference}")
        without_newlines = reference.replace("\u200b", "").replace("\n", " ")
        without_redundant_space = " ".join(without_newlines.split())
        logger.debug(f"Cleaned to: {without_redundant_space}")
        return without_redundant_space

class SubprocessParserMixin(BaseReferenceParser):
    """ Mixin for calling an external routine in a subprocess"""
    CMD = ""

    @classmethod
    def check_cmd(cls):
        if not shutil.which(cls.CMD):
            raise EnvironmentError(f"command `{cls.CMD}` not in path")

    @classmethod
    def call_cmd(cls, *args):
        cls.check_cmd()
        stdout = subprocess.check_output([cls.CMD, *args])
        return stdout.decode("utf-8")


class CermineParser(SubprocessParserMixin):
    accuracy = 50
    NAME = const.CERMINE
    CMD = "cermine"
    ARGS = [
        "pl.edu.icm.cermine.bibref.CRFBibReferenceParser",
        "-format", 'bibtex', "-reference",
    ]

    @classmethod
    def parse_reference(cls, reference, bibtex_parser=None):
        if bibtex_parser is None:
            bibtex_parser = BibTexParser()
        bibtex_reference = cls.call_cmd(*chain(cls.ARGS, (reference,)))
        logger.debug(f"Bibtex {bibtex_reference}")

        result = None

        try:
            result = bibtex_parser.parse(bibtex_reference).get_entry_list()[-1]
        except IndexError:
            # unable to parse
            pass

        fail_message = f'{cls.NAME} was unable to pull a title from {reference}'

        # append a full stop if there is no title returned and re-run
        if not result or not 'title' in result or not result["title"]:
            bibtex_reference = cls.call_cmd(*chain(cls.ARGS, (reference + '.',)))

            try:
                result = bibtex_parser.parse(bibtex_reference).get_entry_list()[-1]
            except IndexError:
                logger.debug(fail_message)
                return None

            if not 'title' in result:
                logger.debug(fail_message)
                return None

        return result


class HTTPBasedParserMixin(BaseReferenceParser):
    """ Mixin for requesting references to be parsed by an HTTP service"""
    REQ_METHOD = ""
    SVC_URL = ""

    def call_svc(self, params=None, data=None):
        svc_caller = getattr(requests, self.REQ_METHOD)
        response = svc_caller()
        return response


class CrossrefParser(HTTPBasedParserMixin):
    """A parser that matches DOIS and retrieves metadata via Crossref API"""
    accuracy = 100
    NAME = const.CROSSREF

    @classmethod
    def parse_reference(cls, reference, bibtex_parser=None):
        ret = None
        crossref_match = const.DOI_RE.search(reference)

        if crossref_match:
            works = Works(etiquette=const.CROSSREF_ETIQUETTE)
            doi = works.doi(crossref_match.group(0))

            if doi:
                ret = {'raw_reference': reference}
                ret['doi'] = crossref_match.group(0)

                ret['author'] = ''
                if 'author' in doi:
                    ret['author'] = ', '.join([f'{author["given"]} {author["family"]}' for author in doi['author']])

                if 'title' in doi:
                    ret['title'] = doi['title'][0]

                if 'container-title' in doi and len(doi['container-title']) > 0:
                    ret['journal'] = doi['container-title'][0]

                if 'volume' in doi:
                    ret['volume'] = doi['volume'][0]

                if 'published-online' in doi:
                    ret['year'] = doi['published-online']['date-parts'][0][0]

        return ret


class BloomsburyAcademicParser(BaseReferenceParser):
    accuracy = 75
    NAME = const.BLOOMSBURY_ACADEMIC


    def parse_reference(cls, reference):
        # create a soup version of the reference
        souped = BeautifulSoup(reference, 'html.parser')
        formatted_reference = {}

        # authors (and editors)
        authors = []
        for soup_author in souped.find_all('span', {'class': 'author'}):
            try:
                authors.append(f'{soup_author.find("span", {"class":"firstname"}).get_text()} '
                               f'{soup_author.find("span", {"class":"surname"}).get_text()}')
            except:
                pass
        for soup_author in souped.find_all('span', {'class': 'editor'}):
            try:
                authors.append(f'{soup_author.find("span", {"class":"firstname"}).get_text()} '
                               f'{soup_author.find("span", {"class":"surname"}).get_text()}')
            except:
                pass
        formatted_reference['author'] = ' ,'.join(authors)

        # year
        try:
            formatted_reference['year'] = souped.find('span', {'class': 'pubdate'}).get_text()
        except:
            formatted_reference['year'] = ''

        # we initially populate title and journal with the same field
        try:
            formatted_reference['title'] = souped.find('span', {'class': 'italic'}).get_text()
            formatted_reference['journal'] = souped.find('span', {'class': 'italic'}).get_text()
        except:
            formatted_reference['title'] = ''
            formatted_reference['journal'] = ''

        # volume
        try:
            formatted_reference['volume'] = souped.find('span', {'class': 'volumenum'}).get_text()
        except:
            formatted_reference['volume'] = ''

        # determine the type of entry
        # if it contains ", in", it's a book chapter
        book_regex = re.compile(r'‘(<i>)*(.+?)(<\/i>)*(<\/span>)*’, in', re.MULTILINE | re.DOTALL)
        match = book_regex.search(reference)
        is_book = False
        if match:
            is_book = True
            formatted_reference['title'] = match.group(2)

        if not is_book:
            # journal articles
            journal_regex = re.compile(r'atitle=(.+?)&', re.MULTILINE | re.DOTALL)
            match = journal_regex.search(reference)
            if match and not '&amp;aulast' in match.group(1):
                formatted_reference['title'] = match.group(1)
            else:
                journal_regex = re.compile(r'‘(.+?)’', re.MULTILINE | re.DOTALL)
                match = journal_regex.search(reference)
                if match:
                    formatted_reference['title'] = match.group(1)
        return formatted_reference


class CambridgeCoreParser(BaseReferenceParser):
    accuracy = 85
    NAME = const.CAMBRIDGE_CORE

    def parse_reference(cls, reference):
        reference_json = json.loads(reference)

        formatted_reference = {}

        # year
        formatted_reference['year'] = reference_json['atom:content']['m:pub-year']

        # title
        if reference_json['atom:content']['m:title'] is not None \
                and reference_json['atom:content']['m:title'] != '':
            formatted_reference['title'] = reference_json['atom:content']['m:title']
        elif reference_json['atom:content']['m:book-title'] is not None \
                and reference_json['atom:content']['m:book-title'] != '':
            formatted_reference['title'] = reference_json['atom:content']['m:book-title']

        # log the raw reference
        formatted_reference['raw_reference'] = reference_json['atom:content']['m:display']

        # journal
        if reference_json['atom:content']['m:journal-title'] != '' \
                and reference_json['atom:content']['m:journal-title'] is not None:
            formatted_reference['journal'] = reference_json['atom:content']['m:journal-title']

        # authors
        formatted_reference['author'] = ''
        for author in reference_json['atom:content']['m:authors']:
            formatted_reference['author'] += f'{author["content"]}, '

        # DOI where it exists
        if reference_json['atom:content']['m:dois'] is not None \
                and len(reference_json['atom:content']['m:dois']) > 0 \
                and reference_json['atom:content']['m:dois'][0]['content'] != '':
            formatted_reference['doi'] = reference_json['atom:content']['m:dois'][0]['content']

        # volume
        if reference_json['atom:content']['m:journal-volume'] != '' and \
                reference_json['atom:content']['m:journal-volume'] is not None:
            formatted_reference['volume'] = reference_json['atom:content']['m:journal-volume']

        formatted_reference['parser'] = cls.NAME

        return formatted_reference
