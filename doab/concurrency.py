import logging
import threading

import requests

logger = logging.getLogger(__name__)
_threadlocal = threading.local()

def get_http_session():
    """ A thread-safe wrapper for requests.session"""
    try:
        return _threadlocal.session
    except AttributeError:
        logger.debug("Starting new HTTP Session")
        _threadlocal.session = requests.Session()
        return get_http_session()
