import sqlalchemy as sql
from sqlalchemy import orm

from porntool import configure
from porntool import util
from porntool import db

def standardSetup(echo=False, file_handler=True):
    configure.load()
    util.configureLogging(file_handler=file_handler)
    engine = sql.create_engine(configure.get('SQL'), echo=echo)
    Session = orm.sessionmaker(bind=engine)
    session = Session()
    db.setSession(session)
