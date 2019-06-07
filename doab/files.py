import os
import logging

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
