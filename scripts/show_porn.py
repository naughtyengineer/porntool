import argparse
import logging
import os.path
import subprocess

import sqlalchemy as sql
from sqlalchemy import orm

import porntool as pt
from porntool import db
from porntool import movie
from porntool import tables
from porntool import util
from porntool import configure
from porntool import player

conf = configure.load()

def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=flexibleBoolean)
args = parser.parse_args()

def addFile(abspath, filepath_list):
    if os.path.isdir(abspath):
        for file_ in os.listdir(abspath):
            if file_[0] == '.':
                continue
            addFile(os.path.join(abspath, file_), filepath_list)
    filepath = movie.getMovie(abspath)
    if filepath:
        filepath_list.append(filepath)

def loadFiles(files):
    if not files:
        return session.query(tables.FilePath).join(tables.MovieFile).filter(
            tables.FilePath.hostname==util.hostname).all()
    else:
        filepath_list = []
        for file_ in files:
            logging.debug('Adding %s', file_)
            abspath = os.path.abspath(file_)
            addFile(abspath, filepath_list)
        return filepath_list

logging.getLogger().handlers=[]
util.configureLogging()
engine = sql.create_engine(conf.get('SQL'), echo=False)
Session = orm.sessionmaker(bind=engine)
session = Session()
db.setSession(session)

filepaths = loadFiles(args.files)
session.commit()

inventory = movie.MovieInventory(filepaths, args.shuffle)

for filepath in inventory:
    player.MoviePlayer(filepath).play()
    q = raw_input('Enter to continue: ')
