from __future__ import division
import logging

import sqlalchemy as sql

from porntool import tables as t

SMART_CUTOFFS = False
try:
    import numpy as np
    from scipy import stats
    from scipy import optimize
    SMART_CUTOFFS = True
except ImportError:
    # would log, but unlikely that any handlers are setup yet
    print('Failed to import numpy or scipy, some features will be disabled')

logger = logging.getLogger(__name__)

class Ratings(object):
    def getRating(self, moviefile):
        pass

    def setRating(self, moviefile, rating):
        pass


def find_stddev(total, mean, target_tens):
    def root_function(stddev):
        not_tens = total * stats.norm.cdf(9, mean, stddev)
        return target_tens - (total - not_tens)
    return optimize.bisect(root_function, 1, 5)


def calculate_cutoffs(raw_rating_values, mean, fraction_tens):
    """returns an array of 11 values, each value is the upper-bound
    of the raw score for the rating with the same index value.  In other words,
    anything with a rating less than the 0th entry, gets a rating of 0.

    The last value isn't necessary but, well, whatever. Shut-up.
    """
    raw_rating_values = np.array(raw_rating_values)
    total = len(raw_rating_values)
    target_tens = total * fraction_tens
    stddev = find_stddev(total, mean, target_tens)
    # even though I don't have anything rated 0, its easier
    # for me to have the indices line up to the ratings (on the cuttoff array)
    indices = np.int16(np.concatenate(
        ([0], total * stats.norm.cdf(range(1, 10), mean, stddev), [-1])))
    return np.sort(raw_rating_values)[indices]


class NormalRatings(Ratings):
    """A rating system that creates a normal distribution of
    ratings between 1-10 for all movies in the collection"""

    def __init__(self, session, fraction_tens=0.01, target_mean=5):
        self.session = session
        self.fraction_tens = fraction_tens
        self.target_mean = target_mean
        self._load()

    def _rawRatingInfo(self, moviefile):
        query = sql.select(
            [t.NormalRating.rating_adjustment,
             sql.func.sum(t.Usage.c.time_), sql.func.count('*')]
        ).select_from(
            t.Usage.join(t.MovieFile).outerjoin(t.NormalRating)
        ).where(
            sql.and_(
                t.MovieFile.active == 1,
                t.MovieFile.id_ == moviefile.id_)
        )
        return self.session.execute(query).fetchone()

    def _rawRating(self, adj, time, cnt):
        if adj is None:
            adj = 5
        return adj * time / cnt

    def _load(self):
        query = sql.select(
            [t.MovieFile.id_, t.NormalRating.rating_adjustment,
             sql.func.sum(t.Usage.c.time_), sql.func.count('*')]
        ).select_from(
            t.Usage.join(t.MovieFile).outerjoin(t.NormalRating)
        ).where(
            t.MovieFile.active == 1
        ).group_by(
            t.MovieFile.id_
        )
        rows = self.session.execute(query).fetchall()
        raw_ratings = [self._rawRating(*r[1:]) for r in rows]
        if SMART_CUTOFFS and len(raw_ratings) > 20:
            self.cutoffs = calculate_cutoffs(raw_ratings, self.target_mean, self.fraction_tens)
        else:
            # do linear ratings instead
            if raw_ratings:
                max_rating = max(int(max(raw_ratings)), 100)
            else:
                max_rating = 100
            step = int(max_rating / 11)
            self.cutoffs = range(0, max_rating, step)

    def getRating(self, moviefile):
        try:
            row = self._rawRatingInfo(moviefile)
            value = self._rawRating(*row)
            for i, c in enumerate(self.cutoffs):
                if value <= c:
                    return i
            return i
        except TypeError:
            logger.exception('Error while trying to get rating for %s', moviefile)
            return 5

    def setRating(self, moviefile, rating):
        # make adjustment to put the rating right in the middle of the
        # desired rating
        need_value = (self.cutoffs[rating] + self.cutoffs[rating - 1]) / 2.0
        _, time_, playcount = self._rawRatingInfo(moviefile)
        new_adjustment = need_value / (time_ / playcount)
        nr = t.NormalRating(file_id=moviefile.id_, rating_adjustment=new_adjustment)
        self.session.merge(nr)
        #nr = self.session.query(t.NormalRating).filter_by(file_id=moviefile.id_).first()
        #nr.rating_adjustment = new_adjustment
        #self.session.commit()
