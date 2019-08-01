import json
import re
from itertools import chain
import logging
import os
import shutil
import subprocess
from os.path import isfile

from crossref.restful import Works

from bs4 import BeautifulSoup
from bibtexparser.bparser import BibTexParser
from doab import const
from sqlalchemy.orm.exc import NoResultFound
import requests

from doab.files import EPUBFileManager, FileManager
from doab.db import models, session_context

logger = logging.getLogger(__name__)


class BaseReferenceParser(object):
    """ A base class for implementing reference parsers

    The entrypoint for the parser is `parser.run()`
    ChildrenMustImplement
        prepare()
        parse_reference()
    The state is preserved under self.references which is a mapping from a
    reference string to a list of parsing results
    :param book_path: (str) The path to the book to be parsed
    """
    def __init__(self, book_id, book_path, *args, **kwargs):
        self.book_path = book_path
        self.book_id = str(book_id)
        self.references = {}

    # a variable that children can override to specify how good they are
    # compared to other parsers
    accuracy = 10

    def prepare(self):
        """ Routines to be run in preparation to parsing the references

        Should populate the self.references map
        """
        raise NotImplementedError

    def parse(self):
        """ The logic for parsing the references

        It reads self.references and adds a tuple of (parser, result)
        to each entry. When overriding, always call super(), as single parser
        may want to implement behaviour from multiple parsers(which is why this
        abstract method doesn't raise NotImplementedError)
        """
        pass

    @classmethod
    def parse_reference(cls, reference):
        return None

    def persist(self, session):
        """ Persists parse results to the database

        :param session: A SQLAlchemy session
        """
        book = session.query(
            models.Book
        ).filter(models.Book.doab_id == self.book_id).one()
        for ref, parses in self.references.items():
            # Link reference with book
            try:
                reference = session.query(
                    models.Reference
                ).filter(models.Reference.id == ref).one()
            except NoResultFound:
                reference = models.Reference(id=ref)
                session.add(reference)
            if reference not in book.references:
                book.references.append(reference)

            # Store parsed reference
            for parse in parses:
                if not parse:
                    logger.debug(f"Reference {ref} has not been parsed")
                    session.commit()
                    continue
                parser_type, parsed = parse
                try:
                    parsed_reference = session.query(
                        models.ParsedReference
                    ).filter(
                        models.ParsedReference.reference_id==reference.id,
                        models.ParsedReference.parser==parser_type,
                    ).one()

                    logger.debug("Existing reference found. Ignoring. Use nuke command to update.")
                except NoResultFound:
                    parsed_reference = models.ParsedReference(
                        reference_id=reference.id,
                        raw_reference=ref,
                        parser=parser_type,
                        authors=parsed.get("author"),
                        title=parsed.get("title"),
                        pages=parsed.get("pages"),
                        journal=parsed.get("journal"),
                        volume=parsed.get("volume"),
                        doi=parsed.get("doi"),
                        year=parsed.get("year"),
                    )
                    session.add(parsed_reference)
                session.commit()

    def echo(self):
        """Prints parse results to stdout"""
        for reference in self.references:
            print(reference)

    def run(self, session=None):
        self.prepare()
        self.parse()
        if session:
            self.persist(session)
        else:
            self.echo()

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

    def __init__(self, *args, **kwargs):
        self.check_cmd()
        super().__init__(*args, **kwargs)

    def check_cmd(self):
        if not shutil.which(self.CMD):
            raise EnvironmentError(f"command `{self.CMD}` not in path")

    @classmethod
    def call_cmd(cls, *args):
        stdout = subprocess.check_output([cls.CMD, *args])
        return stdout.decode("utf-8")


class HTTPBasedParserMixin(BaseReferenceParser):
    """ Mixin for requesting references to be parsed by an HTTP service"""
    REQ_METHOD = ""
    SVC_URL = ""

    def call_svc(self, params=None, data=None):
        svc_caller = getattr(requests, self.REQ_METHOD)
        response = svc_caller()
        return response


class BloomsburyAcademicMixin(BaseReferenceParser):
    HTML_FILTER = (None, None)
    PARSER_NAME = ''

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        book_files = [f for f in os.listdir(book_path) if isfile(os.path.join(book_path, f))]
        self.file_managers = [
            FileManager(os.path.join(book_path, book_file))
            for book_file in book_files
            if '.html' in book_file
            ]

    def prepare(self):
        for file_manager in self.file_managers:
            content = file_manager.read()

            soup = BeautifulSoup(content, "html.parser")
            self.process_soup(soup)

    def parse(self):
        crossref_handler = CrossrefParserMixin(self.book_id, self.book_path)

        for ref in self.references:
            parsed = self.parse_reference(ref)

            logger.debug(f'{self.PARSER_NAME} parsed: {parsed}')
            self.references[ref].append((self.PARSER_NAME, parsed))

            # delegate to crossref handler if we have a DOI
            if 'doi' in parsed:
                doi = crossref_handler.parse_reference(parsed['doi'])
                if doi:
                    logger.debug(f'{crossref_handler.PARSER_NAME} parsed: {doi}')
                    self.references[ref].append((crossref_handler.PARSER_NAME, doi))

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
                print(match.group(1))
                formatted_reference['title'] = match.group(1)
            else:
                journal_regex = re.compile(r'‘(.+?)’', re.MULTILINE | re.DOTALL)
                match = journal_regex.search(reference)
                if match:
                    formatted_reference['title'] = match.group(1)

        return formatted_reference

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        for ref in soup.find_all(name=tag, attrs=attributes):
            clean = self.clean(str(ref))
            self.references[clean] = []


class CambridgeCoreMixin(BaseReferenceParser):
    HTML_FILTER = (None, None)
    PARSER_NAME = ''

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        self.file_manager = FileManager(os.path.join(book_path, const.RECOGNIZED_BOOK_TYPES['CambridgeCore']))

    def prepare(self):
        content = self.file_manager.read()

        # see if we can get an openresolver set to evaluate
        openresolver_regex = r'var openResolverFullReferences = (\[.+\]);'
        or_matches = re.search(openresolver_regex, content, re.MULTILINE)

        if or_matches:
            logger.debug('Using OpenReference variable match')
            reference_list = json.loads(or_matches.group(1))

            for ref in reference_list:
                self.references[json.dumps(ref)] = []
        else:
            logger.debug('Using soup fallback method')
            soup = BeautifulSoup(content, "html.parser")
            self.process_soup(soup)

    def parse(self):
        del_list = []

        crossref_handler = CrossrefParserMixin(self.book_id, self.book_path)

        for ref in self.references:
            parsed = self.parse_reference(ref)
            logger.debug(f'{self.PARSER_NAME} parsed: {parsed}')
            self.references[ref].append((self.PARSER_NAME, parsed))

            # delegate to crossref handler if we have a DOI
            if 'doi' in parsed:
                doi = crossref_handler.parse_reference(parsed['doi'])
                if doi:
                    logger.debug(f'{crossref_handler.PARSER_NAME} parsed: {doi}')
                    self.references[ref].append((crossref_handler.PARSER_NAME, doi))

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

        formatted_reference['parser'] = cls.PARSER_NAME

        return formatted_reference

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        for ref in soup.find_all(name=tag, attrs=attributes):
            clean = self.clean(ref['content'])
            self.references[clean] = []


class EPUBPrepareMixin(BaseReferenceParser):
    HTML_FILTER = (None, None)

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        self.file_manager = EPUBFileManager(os.path.join(book_path, const.RECOGNIZED_BOOK_TYPES['epub']))

    def prepare(self):
        for _, content in self.file_manager.read(mime="application/xhtml+xml"):
            soup = BeautifulSoup(content, "html.parser")
            self.process_soup(soup)

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        for ref in soup.find_all(name=tag, attrs=attributes):
            clean = self.clean(ref.text)
            self.references[clean] = []


class CrossrefParserMixin(HTTPBasedParserMixin):
    accuracy = 100
    PARSER_NAME = 'Crossref'
    """A parser that matches DOIS and retrieves metadata via Crossref API"""

    def prepare(self):
        pass

    def parse(self):
        # using the Crossref approved single DOI: https://www.crossref.org/blog/dois-and-matching-regular-expressions/
        # 'for the 74.9M DOIs we have seen this matches 74.4M of them'

        for ref in self.references:
            parsed = self.parse_reference(ref)
            logger.debug(f'Parsed: {parsed}')
            self.references[ref].append((self.PARSER_NAME, parsed))

    @classmethod
    def parse_reference(cls, reference, bibtex_parser=None):
        crossref_match = const.DOI_RE.search(reference)
        ret = {'parser': cls.PARSER_NAME,
               'raw_reference': reference}

        if crossref_match:
            works = Works(etiquette=const.CROSSREF_ETIQUETTE)
            doi = works.doi(crossref_match.group(0))

            if doi:

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


class CermineParserMixin(SubprocessParserMixin):
    accuracy = 50
    PARSER_NAME = 'Cermine'
    CMD = "cermine"
    ARGS = [
        "pl.edu.icm.cermine.bibref.CRFBibReferenceParser",
        "-format", 'bibtex', "-reference",
    ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bibtex_parser = BibTexParser()

    def parse(self):
        for raw_ref in self.references.keys():
            logger.debug(f"Parsing {raw_ref}")
            result = self.parse_reference(raw_ref, self.bibtex_parser)
            self.references[raw_ref].append((self.CMD, result))

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

        fail_message = f'{cls.PARSER_NAME} was unable to pull a title from {reference}'

        # append a full stop if there is no title returned and re-run
        if not result or not 'title' in result:
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


class PublisherSpecificMixin(object):
    # magic value of 'all' will always return true
    PUBLISHER_NAMES = []
    FILE_TYPES = []

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)

    @classmethod
    def can_handle(cls, book, input_path):
        if 'all' in cls.PUBLISHER_NAMES:
            print(f'The {cls} parser will handle {book.doab_id}')
            return True

        if book.publisher in cls.PUBLISHER_NAMES:
            filetypes = FileManager(os.path.join(input_path, book.doab_id)).types

            for filetype in cls.FILE_TYPES:
                if filetype == 'all':
                    return True

                if filetype not in filetypes:
                    return False

            logger.debug(f'{cls} parser can handle {book.doab_id}')
            return True
        else:
            return False


class PalgraveEPUBParser(CermineParserMixin, EPUBPrepareMixin, PublisherSpecificMixin):
    accuracy = 60
    HTML_FILTER = ("div", {"class": "CitationContent"})
    PUBLISHER_NAMES = ['{"Palgrave Macmillan"}']
    FILE_TYPES = ['epub']
    PARSER_NAME = 'Palgrave Epub'


class CambridgeCoreParser(CambridgeCoreMixin, PublisherSpecificMixin):
    accuracy = 85
    # <meta name = "citation_reference" content = "citation_title=title; citation_author=author;
    # citation_publication_date=1990" >
    HTML_FILTER = ("meta", {"name": "citation_reference"})
    PUBLISHER_NAMES = ['{"Cambridge University Press"}']
    FILE_TYPES = ['CambridgeCore']
    PARSER_NAME = 'Cambridge Core'


class BloomsburyAcademicParser(BloomsburyAcademicMixin, PublisherSpecificMixin):
    accuracy = 75
    # <div class="contribution bibliomixed"><a name="ba-9781849661027-bib31"></a><p class="contribution bibliomixed"><a class="openurl" target="_blank" data-href="?genre=bookitem&amp;title=Democracy and the Rule of Law&amp;atitle=Lineages of the Rule of Law&amp;aulast=Maravall&amp;aufirst=J.&amp;volume=&amp;issue=&amp;pages=&amp;date=2003">
    #       					Find in Library
    #       				</a><span class="bibliomset"><span class="author"><span class="surname">Holmes</span>, <span class="firstname">S.</span></span>
    #       (<span class="pubdate">2003</span>) ‘<i>Lineages of the Rule of Law</i></span>’, in <span class="bibliomset"><span class="editor"><span class="last-first personname"><span class="surname">Maravall</span>, <span class="firstname">J.</span></span></span>
    #       and <span class="editor"><span class="last-first personname"><span class="surname">Przeworksi</span>, <span class="firstname">A.</span></span></span>
    #       (eds), <i><span class="italic emphasis">Democracy and the Rule of Law</span></i>. <span class="address"><span class="city">Cambridge</span></span>:
    #       <span class="publishername">Cambridge University Press</span></span>.</p></div>
    HTML_FILTER = ("div", {"class": "bibliomixed"})
    PUBLISHER_NAMES = ['{"Bloomsbury Academic"}']
    FILE_TYPES = ['all']
    PARSER_NAME = 'Bloomsbury Academic'


def yield_parsers(book, input_path):
    parsers = []
    for parser in PARSERS:
        if parser.can_handle(book, input_path):
            parsers.append(parser)
    return parsers


PARSERS = [PalgraveEPUBParser, CambridgeCoreParser, BloomsburyAcademicParser]
MIXIN_PARSERS = [CermineParserMixin, CrossrefParserMixin]


def get_parser_by_name(parser, mixin_only=True):
    for parse_class in MIXIN_PARSERS:
        if parse_class.PARSER_NAME == parser:
            return parse_class

    if not mixin_only:
        for parse_class in PARSERS:
            if parse_class.PARSER_NAME == parser:
                return parse_class

    return None
