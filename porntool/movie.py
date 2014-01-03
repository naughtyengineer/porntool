import logging
import os.path
import random

import sqlalchemy.orm.exc as sql

from porntool import db
from porntool import tables
from porntool import util
from porntool import filters


logger = logging.getLogger(__name__)

valid_mov_ext = [".avi", ".mpg", ".wmv", ".flv", ".mov", ".mp4",
                 ".vob", ".divx", ".mkv", ".m4v", ".mpeg"]

def getMovie(file_path):
    if not os.path.exists(file_path):
        logger.debug('%s does not exist', file_path)
        return None
    ext = os.path.splitext(file_path)[1]
    base = os.path.basename(file_path)
    if ext not in valid_mov_ext:
        logger.debug('%s does not have a valid extension', file_path)
        return None
    session = db.getSession()
    # need to search to see if this path exists
    try:
        fp = session.query(tables.FilePath).filter(
            tables.FilePath.path==file_path, tables.FilePath.hostname==util.hostname).one()
        return fp
    except sql.NoResultFound:
        pass

    # 2 << 17 = 256kb = 1/4 mb
    # so hashing requires reading a meg of the data
    file_hash = util.hash_file(file_path, 2<<17)
    try:
        mf = session.query(tables.MovieFile).filter(tables.MovieFile.hash_==file_hash).one()
    except sql.NoResultFound:
        logger.info('Adding a new file: %s', file_path)
        mf = tables.MovieFile(hash_=file_hash, active=1, size=os.path.getsize(file_path))
        session.add(mf)
    fp = tables.FilePath(path=file_path, hostname=util.hostname)
    mf.paths.append(fp)
    return fp

class MovieInventory(object):
    def __init__(self, filepaths, shuffle, extra_filters=None, basic_filters=None):
        # suggest putting the computationally cheapest filters first in the list
        self.filepaths = filepaths
        self.shuffle = shuffle
        self.current_movie = 0
        basic_filters = basic_filters if basic_filters else [filters.exists]
        self.filters = basic_filters + (extra_filters if extra_filters else [])

    def __iter__(self):
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
                if not filt(file_):
                    passes_filters = False
                    break
            if passes_filters:
                break
        return file_
