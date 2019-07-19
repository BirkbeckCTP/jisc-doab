from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


def run(task, items, msg, workers, *args, **kwargs):
    total_items = len(items)
    executor = ThreadPoolExecutor(max_workers=workers or 1)
    for item_no, item in enumerate(items):
        log_msg = f"{msg} {item}\t\t[{item_no}/{total_items}]"
        if workers:
            executor.submit(task_wrapper, task, log_msg, item, *args, **kwargs)
        else:
            task_wrapper(task, log_msg, item, *args, **kwargs)


def task_wrapper(task, msg, *args, **kwargs):
    if msg:
        logger.info(msg)
    return task(*args, **kwargs)
