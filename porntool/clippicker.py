import itertools
import logging
import random

from porntool import segment
from porntool import util

logger = logging.getLogger(__name__)

class ClipPicker(object):
    def __init__(self, iinventory, project, ratings, n, segment_tracker_factory):
        self.iinventory = iinventory
        self.project = project
        self.ratings = ratings
        self.segment_tracker_factory = segment_tracker_factory
        self.trackers = []
        self.addTrackers(n)
        self.current_tracker = None
        self.counter = 0

    def _newTracker(self):
        while True:
            try:
                fp = next(self.iinventory)
                break
            except StopIteration:
                logger.info('All out of trackers!')
                raise
            except:
                logger.exception('Failed trying to get next tracker')
        logger.debug('Loading next tracker using %s', fp)
        s = self.segment_tracker_factory(fp, self.project, self.ratings)
        return s

    def addTrackers(self, n=1):
        for _ in range(n):
            try:
                t = self._newTracker()
                logger.debug('Adding tracker: %s', t)
                self.trackers.append(t)
            except StopIteration:
                break
        logger.debug('There are now %s trackers', len(self.trackers))

    def replaceTracker(self, tracker=None):
        tracker = tracker or self.current_tracker
        logger.debug('Removing tracker: %s', tracker)
        self.trackers.remove(tracker)
        self.addTrackers()

    def _nextTracker(self):
        raise NotImplementedError()

    def getNextClip(self):
        if not self.trackers:
            logger.debug('Exiting!')
            return None
        tracker = self._nextTracker()
        self.current_tracker = tracker
        logger.debug('Switching to %s', tracker)
        clip = tracker.nextClip()
        if not clip:
            self.replaceTracker(tracker)
            return self.getNextClip()
        self.counter += 1
        return clip


class Least(object):
    def _nextTracker(self):
        return min(self.trackers, key=lambda t: t.checkedDuration())


class Random(object):
    def _nextTracker(self):
        return random.choice(self.trackers)


def OnlyNClips(N):
    class _OnlyNClips(object):
        def _newTracker(self):
            while True:
                fp = next(self.iinventory)
                clips = [c for c in fp.pornfile._clips if c.project_id == self.project.id_]
                if len(clips) < N:
                    s = self.segment_tracker_factory(fp, self.project, self.ratings)
                    return s
    return _OnlyNClips


class TargetLength(object):
    def __init__(self, iinventory, project, ratings, minutes, segment_tracker_factory):
        self.iinventory = iinventory
        self.project = project
        self.ratings = ratings
        self.segment_tracker_factory = segment_tracker_factory
        self.trackers = []
        self.addTrackers(minutes)
        self.current_tracker = None
        self.counter = 0
        self._all_clips = None

    def addTrackers(self, minutes):
        total = minutes * 60
        so_far = 0
        while so_far <= total:
            try:
                fp = next(self.iinventory)
            except StopIteration:
                break
            clips = [c for c in fp.pornfile._clips if c.project_id == self.project.id_]
            s = self.segment_tracker_factory(fp, self.project, self.ratings)
            so_far += s.length
            self.trackers.append(s)
        logger.debug('There are now %s trackers', len(self.trackers))

    def _processAllClips(self):
        befores, pres, mids, posts = [], [], [], []
        for segment_tracker in self.trackers:
            before, pre, mid, post = segment.segmentClips(segment_tracker)
            befores.append(before)
            pres.append(pre)
            mids.append(mid)
            posts.append(post)
        return itertools.chain.from_iterable((
            util.merge(*befores), util.merge(*pres), util.merge(*mids), util.merge(*posts)))

    def getNextClip(self):
        if not self._all_clips:
            self._all_clips = self._processAllClips()
        return next(self._all_clips, None)
