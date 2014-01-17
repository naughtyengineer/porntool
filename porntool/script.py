import sqlalchemy as sql
from sqlalchemy import orm

from porntool import configure
from porntool import util
from porntool import db

def standardSetup():
    configure.load()
    util.configureLogging()
    engine = sql.create_engine(configure.get('SQL'), echo=False)
    Session = orm.sessionmaker(bind=engine)
    session = Session()
    db.setSession(session)
