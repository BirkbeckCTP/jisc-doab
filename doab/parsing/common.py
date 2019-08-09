from itertools import chain
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class SubprocessMixin(object):
    """ Mixin for calling an external command in a subprocess"""
    CMD = ""
    ARGS = []

    @classmethod
    def check_cmd(cls):
        if not shutil.which(cls.CMD):
            raise EnvironmentError(f"command `{cls.CMD}` not in path")

    @classmethod
    def call_cmd(cls, *args):
        cls.check_cmd()
        logger.debug(f"Spawning process to run {cls.CMD}")
        stdout = subprocess.check_output([cls.CMD, *chain(cls.ARGS, args)])
        return stdout.decode("utf-8")


class CleanReferenceMixin(object):
    """Mixin that provides a clean() staticmethod for cleaning ar reference"""

    @staticmethod
    def clean(reference):
        logger.debug(f"Cleaning {reference}")
        without_newlines = reference.replace("\u200b", "").replace("\n", " ")
        without_redundant_space = " ".join(without_newlines.split())
        logger.debug(f"Cleaned to: {without_redundant_space}")
        return without_redundant_space

