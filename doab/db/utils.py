import os

def get_dsn():
    return "postgres://%s:%s@%s/%s" % (
        os.getenv("DOAB_DB_USER", "root"),
        os.getenv("DOAB_DB_PASSWORD", "root"),
        os.getenv("DOAB_DB_HOST", "db"),
        os.getenv("DOAB_DB_NAME", "doab"),
    )
