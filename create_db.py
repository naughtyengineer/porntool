import os.path

import sqlalchemy

from porntool import configure
from porntool import db
from porntool import tables

configure.load()

SQL_FILE = configure.get('SQL_FILE')
if not SQL_FILE:
    raise Exception('The location of the database (SQL_FILE) is not specified.')

if os.path.exists(SQL_FILE):
    raise Exception("The file %s already exists.  Can't create database", SQL_FILE)

engine = sqlalchemy.create_engine(db.urlFromFile(SQL_FILE), echo=False)
tables.Base.metadata.create_all(engine)
print "Succesfully created a new database: {}".format(SQL_FILE)
