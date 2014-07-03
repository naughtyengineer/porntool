import argparse
import datetime
import logging
import random
import os.path

import sqlalchemy as sql

from porntool import tables as t
from porntool import util

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

# class RatingRecent(object):
#     def __call__(self, movie):
#         return _play_recentrating(movie.count, movie.rating, movie.last)

class Exists(object):
    def __call__(self, filepath):
        return os.path.exists(filepath.path)


class IsMovie(object):
    def __call__(self, filepath):
        ext = os.path.splitext(filepath.path)[1]
        return ext in util.valid_mov_ext


class IncludeTags(object):
    def __init__(self, tags):
        self.tags = set(tags)

    def __call__(self, filepath):
        return (set([t.tag for t in filepath.pornfile.tags]) & self.tags) == self.tags


class ExcludeTags(object):
    def __init__(self, tags):
        self.tags = set(tags)

    def __call__(self, filepath):
        return len(set([t.tag for t in filepath.pornfile.tags]) & self.tags) == 0


class IncludeGirls(object):
    def __init__(self, girls):
        self.girls = set(girls)

    def __call__(self, filepath):
        return len(set([g.name for g in filepath.pornfile.girls]) & self.girls) > 0


class ExcludeGirls(object):
    def __init__(self, girls):
        self.girls = set(girls)

    def __call__(self, filepath):
        return len(set([g.name for g in filepath.pornfile.girls]) & self.girls) == 0


class ByMaxCount(object):
    def __init__(self, session, count):
        self.session = session
        self.count = count

    def __call__(self, filepath):
        return filepath.pornfile.getPlayCount(self.session) <= self.count


class ByMinCount(object):
    def __init__(self, session, count):
        self.session = session
        self.count = count

    def __call__(self, filepath):
        return filepath.pornfile.getPlayCount(self.session) >= self.count


class ExcludeFilenames(object):
    def __init__(self, filenames):
        self.filenames = set(filenames)

    def __call__(self, filepath):
        return filepath.path not in self.filenames


def getParser():
    PARSER = argparse.ArgumentParser(add_help=False)
    PARSER.add_argument('--max-count', type=int)
    PARSER.add_argument('--min-count', type=int)
    PARSER.add_argument('--include-tags', nargs="+")
    PARSER.add_argument('--exclude-tags', nargs="+")
    PARSER.add_argument(
        '--exclude-files', nargs="+", help="a file containing a list of filenames to exclude")
    PARSER.add_argument('--include-girls', nargs="+")
    PARSER.add_argument('--exclude-girls', nargs="+")
    return PARSER

def applyArgs(args, session):
    all_filters = []
    if args.min_count is not None:
        all_filters.append(ByMinCount(session, args.min_count))
    if args.max_count is not None:
        all_filters.append(ByMaxCount(session, args.max_count))
    if args.include_tags:
        all_filters.append(IncludeTags(args.include_tags))
    if args.exclude_tags:
        all_filters.append(ExcludeTags(args.exclude_tags))
    if args.include_girls:
        all_filters.append(IncludeGirls(args.include_girls))
    if args.exclude_girls:
        all_filters.append(ExcludeGirls(args.exclude_girls))
    if args.exclude_files:
        for filename in args.exclude_files:
            with open(filename) as f:
                e = ExcludeFilenames([l.strip() for l in f])
                all_filters.append(e)
    return all_filters
