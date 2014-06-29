import hashlib
import logging
import os
import os.path
import platform
import random
import subprocess
import sys

import numpy as np

from porntool import configure
from porntool import db

logger = logging.getLogger(__name__)

hostname = platform.node()
_dot = hostname.find('.')
if _dot > 0:
    hostname = hostname[:_dot]


DEVNULL = open(os.devnull, 'w')


valid_mov_ext = [".avi", ".mpg", ".wmv", ".flv", ".mov", ".mp4",
                 ".vob", ".divx", ".mkv", ".m4v", ".mpeg"]


class Namespace(object):
    def __init__(self, attr_dict):
        self.__dict__.update(attr_dict)


def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')


def hash_file(file_, sample_size, enable_warn=True):
    logger.info("Hashing %s", file_)
    sample_points = 4
    file_size = os.path.getsize(file_)
    if enable_warn and file_size < (sample_size * 4):
        logger.warn('Hashing %s despite being a small file')
    h = hashlib.sha1()
    f = open(file_)
    size = min(file_size / sample_points, sample_size)
    for i in range(0,sample_points):
        seek = i * file_size / sample_points
        f.seek(seek)
        h.update(f.read(size))
    hash = h.hexdigest()
    return hash


def standardConsoleHandler():
    result = logging.StreamHandler(sys.stdout)
    format_ = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    formatter = logging.Formatter(format_)
    result.setFormatter(formatter)
    return result


def standardFileHandler(filename):
    result = logging.FileHandler(filename)
    format_ = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    formatter = logging.Formatter(format_)
    result.setFormatter(formatter)
    return result


def configureLogging(level=logging.DEBUG, file_handler=True):
    if file_handler:
        logging.getLogger().addHandler(standardFileHandler('log'))
    else:
        logging.getLogger().addHandler(standardConsoleHandler())
    logging.getLogger().setLevel(level)
    logging.getLogger('urwid').setLevel('WARNING')


class Weights(object):
    def __init__(self, weights):
        self.weights = weights

    def _head(self, index):
        assert len(index) == len(self.weights)
        for i, w in zip(index, self.weights):
            if i < len(w):
                yield w[i]
            else:
                yield 0

    def sum(self, index):
        return sum(self._head(index))

    def getIndex(self, target_value, index):
        assert target_value < self.sum(index)
        lower_bound = 0
        for i, value in enumerate(self._head(index)):
            upper_bound = lower_bound + value
            if lower_bound <= target_value < upper_bound:
                return i
            lower_bound = upper_bound
        raise Exception("Can't get here")

    def random(self, index):
        s = self.sum(index)
        if s:
            r = random.random() * s
            return self.getIndex(r, index)
        else:
            # if all the weights sum to zero, we're done
            return None


def merge(items, weights=None):
    """Randomly merges `items` together.

    Args:
        items: a list of lists
        weights: weights to base the random selection off of
    """
    indexes = [0] * len(items)
    if not weights:
        weights = []
        for item_list in items:
            weights.append([1 for i in item_list])
    weights = Weights(weights)
    while True:
        j = weights.random(indexes)
        if j is None:
            break
        i = indexes[j]
        yield items[j][i]
        indexes[j] += 1
