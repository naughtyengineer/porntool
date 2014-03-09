import logging
import os.path
import random

import sqlalchemy.orm.exc as sql

from porntool import db
from porntool import tables
from porntool import util
from porntool import filters
from porntool import player


logger = logging.getLogger(__name__)

valid_mov_ext = [".avi", ".mpg", ".wmv", ".flv", ".mov", ".mp4",
                 ".vob", ".divx", ".mkv", ".m4v", ".mpeg"]

def updateMissingProperties(file_path):
    moviefile = file_path.pornfile
    if moviefile.length is None:
        mp = player.MoviePlayer(file_path.path)
        mp.identify()
        moviefile.length = mp.length

def addMovie(filename):
   # 2 << 17 = 256kb = 1/4 mb
    # so hashing requires reading a meg of the data
    file_hash = util.hash_file(filename, 2<<17)
    session = db.getSession()
    try:
        mf = session.query(tables.MovieFile).filter(tables.MovieFile.hash_==file_hash).one()
    except sql.NoResultFound:
        logger.info('Adding a new file: %s', filename)
        mf = tables.MovieFile(hash_=file_hash, active=1, size=os.path.getsize(filename))
        session.add(mf)
    fp = tables.FilePath(path=filename, hostname=util.hostname)
    mf.paths.append(fp)

def getMovie(filename, add_movie=None):
    if not os.path.exists(filename):
        logger.debug('%s does not exist', filename)
        return None
    ext = os.path.splitext(filename)[1]
    base = os.path.basename(filename)
    if ext not in valid_mov_ext:
        return None
    session = db.getSession()
    # need to search to see if this path exists
    try:
        fp = session.query(tables.FilePath).filter(
            tables.FilePath.path==filename, tables.FilePath.hostname==util.hostname).one()
        return fp
    except sql.NoResultFound:
        logger.debug('No filepath found for %s:%s', util.hostname, filename)

    if not add_movie:
        return None
    fp = add_movie(filename)
    return fp


def checkAndAddFile(abspath, filepath_list, add_movie):
    logger.debug('Checking %s', abspath)
    if os.path.isdir(abspath):
        for file_ in os.listdir(abspath):
            if file_[0] == '.':
                continue
            checkAndAddFile(os.path.join(abspath, file_), filepath_list, add_movie)
    filepath = getMovie(abspath, add_movie)
    if filepath:
        filepath_list.append(filepath)


def loadFiles(files=None, add_movie=None):
    if not files:
        return db.getSession().query(tables.FilePath).join(tables.MovieFile).filter(
            tables.FilePath.hostname==util.hostname).all()
    else:
        filepath_list = []
        for file_ in files:
            file_ = file_.decode('utf-8')
            logging.debug('Adding %s', file_)
            abspath = os.path.abspath(file_)
            checkAndAddFile(abspath, filepath_list, add_movie)
        return filepath_list


class MovieInventory(object):
    """Provides an iterator over filepaths that meet the given filters and
    ordering/shuffle.
    """
    def __init__(self, filepaths, shuffle, extra_filters=None, basic_filters=None):
        # suggest putting the computationally cheapest filters first in the list
        self.filepaths = filepaths
        self.shuffle = shuffle
        self.current_movie = 0
        basic_filters = basic_filters if basic_filters else [filters.exists]
        self.filters = basic_filters + (extra_filters if extra_filters else [])

    def __iter__(self):
        self.current_movie = 0
        return self

    def next(self):
        while True:
            lng = len(self.filepaths)
            if self.current_movie >= lng:
                raise StopIteration

            file_ = self.filepaths[self.current_movie]
            if self.shuffle:
                # get a random file that hasn't been choosen yet
                j = random.randint(self.current_movie, lng - 1)
                # swap that file into the 'correct' position
                tmp = self.filepaths[j]
                self.filepaths[j] = file_
                self.filepaths[self.current_movie] = tmp
                file_ = tmp
            self.current_movie += 1

            passes_filters = True
            for filt in self.filters:
                if filt and not filt(file_):
                    passes_filters = False
                    break
            if passes_filters:
                break
        return file_
