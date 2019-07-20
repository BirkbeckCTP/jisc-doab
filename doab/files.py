import logging
from operator import itemgetter
import os
import zipfile

from ebooklib import epub

logger = logging.getLogger(__name__)


class FileManager():
    def __init__(self, base_path):
        if not base_path.startswith("/"):
            base_path = os.path.join(os.getcwd(), base_path)
        self.base_path = base_path
        logger.debug("File manager will write to %s" % self.base_path)

    def write_bytes(self, *path_parts, filename, to_write):
        path_parts = (str(part) for part in path_parts)
        dir_path = path = os.path.join(self.base_path, *path_parts)
        self.makedirs(dir_path)
        path = os.path.join(dir_path, filename)
        with open(path, "wb") as f:
            f.write(to_write)

    def makedirs(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def list(self, *path_parts, hidden=False):
        path = os.path.join(self.base_path, *path_parts)
        li = os.listdir(os.path.join(self.base_path, *path_parts))
        if not hidden:
            return [i for i in li if not i.startswith(".")]

    def read(self, *path_parts, mode=""):
        read_path = os.path.join(self.base_path, *path_parts)
        with open(read_path, f"r{mode}") as read_file:
            return read_file.read()

    def unzip(self, *path_parts, out=None):
        """Extracts the contents into memory or to a file
        :param *path_parts: aany number of parts to be joined for the path
        :param out: The output path for extracting the contents. If set to None
            it will extract in memory
        """
        read_path = os.path.join(self.base_path, *path_parts)
        zip_file = self._get_zipfile(read_path)
        if out:
            zip_file.extractall(out)
        else:
            for name in zipfile.namelist():
                content = zipfile.read(name)
                yield content

    def _get_zipfile(self, path, mode="r"):
        return zipfile.ZipFile(path, mode)

class EPUBFileManager(FileManager):
    def __init__(self, base_path):
        super().__init__(base_path)
        self.epub_filename = base_path
        self.epub_file = None

    @property
    def is_epub(self):
        return True if os.path.exists(self.epub_filename) else False

    def read(self, filename=None, mime=None):
        """Returns the contents of the epub file
        :param filename: A string identifying a filename from the epub
        :param mime: A MIME by which to filter the items to be read
        :return: The contents of a file or an iterable of tuples
            of the format (filename, contents)
        """
        if not self.epub_file:
            self.epub_file = epub.read_epub(self.epub_filename) if os.path.exists(self.epub_filename) else None

        for item in self.epub_file.items:
            name = item.get_name()
            if filename:
                if filename == name:
                    return name, item.get_content()
            elif mime:
                if mime == item.media_type:
                    yield name, item.get_content()
            else:
                yield name, item.get_content()

    def list(self):
        """ Lists all the items available in the epub document and their MIMEs

        :return: A list of tuples of the format (MIME, filename)
        """
        if not self.epub_file:
            self.epub_file = epub.read_epub(self.epub_filename) if os.path.exists(self.epub_filename) else None

        return [
            (item.media_type, item.get_name())
            for item in self.epub_file.items
        ]

    def write_bytes(self, *args, **kwargs):
        raise NotImplementedError


