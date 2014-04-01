import datetime
import logging
import random
import os.path

import sqlalchemy as sql

from porntool import tables as t

logger = logging.getLogger(__name__)

def _play_recentrating(count, rating, last):
    if last is None:
        print "No Last"
        return True
    last = datetime.datetime.strptime(last, '%Y-%m-%d %H:%M:%S.%f')
    rating_play_map = {10:4.0, 9:3.5, 8:3.0, 7:2.5, 6:2.0,
                       5:1.75, 4:1.5, 3:1.25}
    play_cnt = rating_play_map.get(rating, 1)
    freq = (2 * 365.0 * 24 * 60 * 60) / play_cnt # how often, in seconds, to play a video
    print "Target:", (2 * 365.0) / play_cnt, "Actual:", (datetime.datetime.now() - last).days
    since_last = (datetime.datetime.now() - last).total_seconds()
    rnd = random.random()
    prob = since_last / freq

    # add some adjustments to favor movies with lower watch counts
    if count == 0:
        prob = 1.0
    elif count == 1:
        prob = min(1, prob * 3)
    elif count == 2:
        prob = min(1, prob * 2)
    print "Prob = %s, Random = %s" % (prob, rnd)
    return  rnd < (prob)

class RatingRecent(object):
    def __call__(self, movie):
        return _play_recentrating(movie.count, movie.rating, movie.last)

class Exists(object):
    def __call__(self, filepath):
        return os.path.exists(filepath.path)

class IncludeTags(object):
    def __init__(self, tags):
        self.tags = set(tags)

    def __call__(self, filepath):
        return len(set([t.tag for t in filepath.pornfile.tags]) & self.tags) > 0

class ExcludeTags(object):
    def __init__(self, tags):
        self.tags = set(tags)

    def __call__(self, filepath):
        return len(set([t.tag for t in filepath.pornfile.tags]) & self.tags) == 0

class ByCount(object):
    def __init__(self, session, count):
        self.session = session
        self.count = count

    def __call__(self, filepath):
        return filepath.pornfile.getPlayCount(self.session) <= self.count
