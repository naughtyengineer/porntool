import logging
import random

logger = logging.getLogger(__name__)

class ClipPicker(object):
    def __init__(self, iinventory, ratings, n=20, tracker_factory=None):
        self.iinventory = iinventory
        self.ratings = ratings
        self.tracker_factory = tracker_factory
        self.trackers = []
        self.addTrackers(n)
        self.current_tracker = None

    def _newTracker(self):
        fp = next(self.iinventory)
        s = self.tracker_factory(fp, self.ratings)
        return s

    def addTrackers(self, n=1):
        for _ in range(n):
            try:
                self.trackers.append(self._newTracker())
            except StopIteration:
                break

    def removeTracker(self, tracker=None):
        tracker = tracker or self.current_tracker
        logger.debug('Removing tracker: %s', tracker)
        self.trackers.remove(tracker)
        try:
            t = self._newTracker()
            logger.debug('Adding tracker: %s', t)
            self.trackers.append(t)
        except StopIteration:
            pass

    def _nextTracker(self):
        return min(self.trackers, key=lambda t: t.checkedDuration())

    def getNextClip(self):
        if not self.trackers:
            logger.debug('Exiting!')
            return None
        tracker = self._nextTracker()
        self.current_tracker = tracker
        logger.debug('Switching to %s', tracker)
        clip = tracker.nextClip()
        if not clip:
            self.removeTracker(tracker)
            return self.getNextClip()
        return clip


class RandomClipPicker(ClipPicker):
    def _nextTracker(self):
        return random.choice(self.trackers)


class OnlyNewClips(RandomClipPicker):
    def _newTracker(self):
        while True:
            fp = next(self.iinventory)
            if len(fp.pornfile.clips) == 0:
                s = self.tracker_factory(fp)
                return s
