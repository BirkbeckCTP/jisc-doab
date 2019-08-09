import json
import logging
import os
from os.path import isfile
import re

from bs4 import BeautifulSoup

from doab import const
from doab.files import EPUBFileManager, FileManager

logger = logging.getLogger(__name__)

class BaseReferenceFinder(object):
    def __init__(self, book_id, book_path, *args, **kwargs):
        self.book_id = book_id
        self.book_path = book_path

    def find(self):
        """ Routines to be run in preparation to parsing the references

        Should populate the self.references map
        """
        raise NotImplementedError

    @staticmethod
    def clean(reference):
        logger.debug(f"Cleaning {reference}")
        without_newlines = reference.replace("\u200b", "").replace("\n", " ")
        without_redundant_space = " ".join(without_newlines.split())
        logger.debug(f"Cleaned to: {without_redundant_space}")
        return without_redundant_space


class EPUBReferenceFinder(BaseReferenceFinder):
    HTML_FILTER = (None, None)

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        self.file_manager = EPUBFileManager(os.path.join(book_path, const.RECOGNIZED_BOOK_TYPES['epub']))

    def find(self):
        references = set()
        for _, content in self.file_manager.read(mime="application/xhtml+xml"):
            soup = BeautifulSoup(content, "html.parser")
            references |= self.process_soup(soup)

        return references

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        return {
            self.clean(ref.text)
            for ref in soup.find_all(name=tag, attrs=attributes)
        }


class SpringerEPUBReferenceFinder(EPUBReferenceFinder):
    HTML_FILTER = ("div", {"class": "CitationContent"})


class BloomsburyReferenceFinder(BaseReferenceFinder):
    HTML_FILTER = ("div", {"class": "bibliomixed"})
    # <div class="contribution bibliomixed"><a name="ba-9781849661027-bib31"></a><p class="contribution bibliomixed"><a class="openurl" target="_blank" data-href="?genre=bookitem&amp;title=Democracy and the Rule of Law&amp;atitle=Lineages of the Rule of Law&amp;aulast=Maravall&amp;aufirst=J.&amp;volume=&amp;issue=&amp;pages=&amp;date=2003">
    #       					Find in Library
    #       				</a><span class="bibliomset"><span class="author"><span class="surname">Holmes</span>, <span class="firstname">S.</span></span>
    #       (<span class="pubdate">2003</span>) ‘<i>Lineages of the Rule of Law</i></span>’, in <span class="bibliomset"><span class="editor"><span class="last-first personname"><span class="surname">Maravall</span>, <span class="firstname">J.</span></span></span>
    #       and <span class="editor"><span class="last-first personname"><span class="surname">Przeworksi</span>, <span class="firstname">A.</span></span></span>
    #       (eds), <i><span class="italic emphasis">Democracy and the Rule of Law</span></i>. <span class="address"><span class="city">Cambridge</span></span>:
    #       <span class="publishername">Cambridge University Press</span></span>.</p></div>

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        book_files = [f for f in os.listdir(book_path) if isfile(os.path.join(book_path, f))]
        self.file_managers = [
            FileManager(os.path.join(book_path, book_file))
            for book_file in book_files
            if '.html' in book_file
        ]

    def find(self):
        references = set()
        for file_manager in self.file_managers:
            content = file_manager.read()

            soup = BeautifulSoup(content, "html.parser")
            references |= self.process_soup(soup)
        return references

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        return {
            self.clean(str(ref))
            for ref in soup.find_all(name=tag, attrs=attributes)
        }



class CambridgeReferenceFinder(BaseReferenceFinder):
    HTML_FILTER = ("meta", {"name": "citation_reference"})

    def __init__(self, book_id, book_path, *args, **kwargs):
        super().__init__(book_id, book_path, *args, **kwargs)
        self.file_manager = FileManager(os.path.join(book_path, const.RECOGNIZED_BOOK_TYPES['CambridgeCore']))

    def find(self):
        references = set()
        content = self.file_manager.read()

        # see if we can get an openresolver set to evaluate
        openresolver_regex = r'var openResolverFullReferences = (\[.+\]);'
        or_matches = re.search(openresolver_regex, content, re.MULTILINE)

        if or_matches:
            logger.debug('Using OpenReference variable match')
            reference_list = json.loads(or_matches.group(1))

            for ref in reference_list:
                references.add(json.dumps(ref))
        else:
            logger.debug('Using soup fallback method')
            soup = BeautifulSoup(content, "html.parser")
            references = self.process_soup(soup)

        return references

    def process_soup(self, soup):
        tag, attributes = self.HTML_FILTER
        return {
            self.clean(ref['content'])
            for ref in soup.find_all(name=tag, attrs=attributes)
        }
