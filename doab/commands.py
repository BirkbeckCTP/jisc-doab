from concurrent.futures import ThreadPoolExecutor

from doab import const
from doab.client import DOABOAIClient
from doab.files import FileManager


def print_publishers():
    for pub in const.Publisher:
        print(f"{pub.value}\t{pub.name}")


def extractor(publisher_id, output_path, multithread=False):
    executor = ThreadPoolExecutor(max_workers=15)
    writer = FileManager(output_path)
    client = DOABOAIClient()
    if publisher_id == "all":
        records = client.fetch_all_records()
    else:
        records = client.fetch_records_for_publisher_id(publisher_id)
    for record in records:
        print(f"Ectracting Corpus for DOAB record with ID {record.doab_id}")
        if multithread:
            executor.submit(record.persist, writer)
        else:
            record.persist(writer)