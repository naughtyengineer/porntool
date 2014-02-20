import logging
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

def standardSetup(echo=False, file_handler=True, copy_db=True):
    global SQL_FILE, TMP_FILE, COPIED
    configure.load()
    util.configureLogging(file_handler=file_handler)
    # I store my database in dropbox and the incremental updates
    # while running the program can get expensive
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
