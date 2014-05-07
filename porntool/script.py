import logging
import os.path
import shutil
import tempfile

import sqlalchemy as sql
from sqlalchemy import orm

from porntool import configure
from porntool import util
from porntool import db

logger = logging.getLogger(__name__)

SQL_FILE = None
TMP_FILE = None
COPIED = None

class LockFile():
    def __init__(self):
        self.lockfile = configure.get('SQL_FILE') + '.lock'
        self.delete = True

    def lock(self):
        if os.path.exists(self.lockfile):
            self.delete = False
            raise Exception('Database lockfile (%s) already exists', self.lockfile)
        with open(self.lockfile, 'w'):
            pass

    def unlock(self):
        if self.delete:
            try:
                os.remove(self.lockfile)
            except OSError:
                pass

LOCK_FILE = None

def standardSetup(echo=False, file_handler=True, copy_db=True):
    """Utility function to setup up the configuration, logging and database

    Args:
        echo: enable sqlalchemy db echoing
        file_handler: log to a file if True, log to screen if False
        copy_db: write changes to a copy of the database, which upon cleanup replaces
            the existing one
    """
    global SQL_FILE, TMP_FILE, COPIED, LOCK_FILE
    configure.load()
    util.configureLogging(file_handler=file_handler)
    # I store my database in dropbox and the incremental updates
    # while running the program can get expensive
    LOCK_FILE = LockFile()
    LOCK_FILE.lock()
    SQL_FILE = configure.get('SQL_FILE')
    COPIED = copy_db
    if copy_db:
        TMP_FILE = tempfile.NamedTemporaryFile()
        logger.debug('Temp database is %s', TMP_FILE.name)
        with open(SQL_FILE) as f:
            shutil.copyfileobj(f, TMP_FILE)
            TMP_FILE.flush()
        engine = sql.create_engine(db.urlFromFile(TMP_FILE.name), echo=echo)
    else:
        engine = sql.create_engine(db.urlFromFile(SQL_FILE), echo=echo)
    Session = orm.sessionmaker(bind=engine)
    session = Session()
    db.setSession(session)


def standardCleanup():
    if COPIED:
        # can't close because TMP_FILE deletes on close
        TMP_FILE.flush()
        shutil.copyfile(TMP_FILE.name, SQL_FILE)
    if LOCK_FILE:
        LOCK_FILE.unlock()
