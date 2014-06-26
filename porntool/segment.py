import collections
import logging
import random

import sqlalchemy as sql

from porntool import db
from porntool import tables as t

logger = logging.getLogger(__name__)

PotentialClip = collections.namedtuple('PotentialClip', ['start', 'end', 'priority'])
Scrub = collections.namedtuple('Scrub', ['start', 'end'])

class SegmentTracker(object):
    def __init__(self, filepath, project, ratings):
        self.filepath = filepath
        self.project = project
        self.ratings = ratings
        self.rows = self.getRows()
        self.total_clips = len(self.rows)
        self.checked_clips = 0
        self.current_row = 0

    def __iter__(self):
        while True:
            c = self.nextClip()
            if c:
                yield c
            else:
                break

    def getClips(self):
        return [c for c in self.filepath.pornfile._clips if c.project_id == self.project.id_]

    def __str__(self):
        return  u'{}<{}>'.format(self.__class__.__name__, self.filepath.path)

    def _length(self):
        return random.choice([2, 2, 2, 2, 3, 3, 3, 4, 4, 5, 6, 7, 8])

    def checkedDuration(self):
        dur = sum(c.duration for c in self.getClips())
        #logger.debug("Duration for %s: %s", self, dur)
        return dur

    def addRow(self, sorted_rows, start, end, priority):
        if not sorted_rows:
            sorted_rows.append(PotentialClip(start, end, priority))
            return
        previous_row = (0, 0)
        for row in sorted_rows:
            if start < row[0]:
                break
            previous_row = row
        if start >= previous_row[1]:
            # either the candidate fits in the gap
            # or its after all the existing rows
            if end <= row[0] or previous_row == row:
                sorted_rows.append(PotentialClip(start, end, priority))
                sorted_rows.sort()

    def traverseGaps(self, rows, start, movie_end, margin=0):
        """Find a place for a new clip that doesn't overlap with existing clips

        Args:
            rows: current clips
            start: time to start the new clip. `start` is in 'gap
                terms', not absolute terms. so, if start is 10 seconds
                - it means ten seconds worth of gap if the first
                minute is already in `rows`, then the start would
                actually be 1:10.
            movie_end: total length of the movie
            margin: buffer around each existing clip to not allow new ones

        Returns: (location in absolute terms, remaining duration in the current gap)
        """
        if not rows:
            return start, movie_end - start
        total_gaps = 0
        last_end = 0
        gap_found = False
        for pc in rows:
            margined_start = pc.start - margin
            # have to take the maximum because it is possible that
            # (start - margin) < ((end of previous clip) + margin)
            # in which case we don't want a negative gap.
            current_gap = max(margined_start - last_end, 0)
            if total_gaps <= start < (total_gaps + current_gap):
                # the target location is in this gap!
                gap_found = True
                break
            total_gaps += current_gap
            last_end = pc.end + margin

        location = last_end + (start - total_gaps)
        if gap_found:
            remaining = margined_start - location
        else:
            # its possible that (endprevious clip + margin) > movie_end
            # so just want to return that there is 0 remaining
            remaining = max(movie_end - location, 0)
        return location, remaining

    def addRowsByFlag(self, rows):
        pornfile = self.filepath.pornfile
        flags = db.getSession().query(t.Flag).filter(
            t.Flag.file_id==pornfile.id_).all()
        # with a flag, we want to do +/- 5 around it, split randomlyish
        for flag in flags:
            start = flag.location - 5
            while start < flag.location + 5:
                end = start + self._length()
                self.addRow(rows, start, end, 0)
                start = end


    def addRowsByScrubs(self, rows):
        pornfile = self.filepath.pornfile
        query = sql.select(
            [t.Scrub.c.start, t.Scrub.c.end]
        ).select_from(
            t.Scrub
        ).where(
            t.Scrub.c.file_id == pornfile.id_)

        scrubs = sorted([Scrub(s, e) for s,e in db.getSession().execute(query).fetchall()])
        last_end = 0
        for scrub in scrubs:
            start = scrub.start
            end = scrub.end
            # deal with overlap
            if end < last_end:
                continue
            if start < last_end:
                start = last_end
            last_end = end
            while True:
                clip_length = end - start
                # ignore the short stuff
                if end - start < 1:
                    break
                target_length = self._length()
                if clip_length > target_length:
                    self.addRow(rows, start, start + target_length, 1)
                    # skip ahead some bit to make it interesting
                    start = start + target_length + random.randint(10, 20)
                else:
                    self.addRow(rows, start, end, 1)
                    break

    def addRowsUniform(self, rows, target_fraction=None, count=None):
        pornfile = self.filepath.pornfile
        duration = sum(pc.end - pc.start for pc in rows)

        if target_fraction:
            # fill in gaps to get to get the target_fraction:
            logger.info(
                'Rating: %s; target fraction: %s; current fraction: %s',
                rating, target_fraction, duration / pornfile.length)
            def condCheck():
                return duration / pornfile.length < target_fraction
        elif count:
            logger.info('Current rows: %s, target: %s for %s', len(rows), count, self)
            def condCheck():
                return len(rows) < count
        else:
            raise Exception('either target_fraction or count must be specified')

        # we first try large margins, and if that fails a lot
        # we reduce the margin and try again, and again, and again
        existing_rows = len(rows)
        for margin in (120, 60, 30, 10, 0):
            if not condCheck():
                break
            failed_count = 0
            while condCheck() and failed_count < 10:
                start = round(random.random() * (pornfile.length - duration), 1)
                location, remaining = self.traverseGaps(rows, start, pornfile.length, margin)
                if remaining < 1.5:
                    failed_count += 1
                    continue
                length = min(remaining, self._length())
                end = location + length
                # don't need to check this, know its in a gap
                rows.append(PotentialClip(location, end, 2))
                rows.sort()
                duration += length
            logger.debug('For margin %s, found %s rows', margin, len(rows) - existing_rows)
            existing_rows = len(rows)

    def getRows(self):
        pornfile = self.filepath.pornfile
        logger.debug('Getting Rows for %s', self)

        # first load up the existing clips
        rows = [PotentialClip(c.start, c.end, 0) for c in
                sorted(self.getClips(), key=lambda clip: clip.start)]

        self.addRowsByFlag(rows)
        self.addRowsByScrubs(rows)

        rating = self.ratings.getRating(pornfile)
        target_fraction = .04 * rating
        self.addRowsUniform(rows, target_fraction)

        logger.debug('Done getting rows for %s', self)
        return rows

    def _makeClip(self, **kwargs):
        clip = t.Clip(**kwargs)
        db.getSession().add(clip)
        db.getSession().flush()
        return clip


    def _checkCandidate(self, potential_clip):
        start = potential_clip.start
        end = potential_clip.end
        overlap_found = False
        existing_clips = self.getClips()
        for eclip in existing_clips:
            if eclip.start <= start <= eclip.end:
                overlap_found = True
                break
            if eclip.start <=end <= eclip.end:
                overlap_found = True
                break
        if overlap_found:
            logger.debug('Overlap found.  Skipping')
            return None
        return self._makeClip(
            file_id=self.filepath.file_id, project_id=self.project.id_, start=start,
            duration=end-start)


    def _nextClip(self):
        while self.current_row < len(self.rows):
            logger.debug("Current Row: %s", self.current_row)
            potential_clip = self.rows[self.current_row]
            self.current_row += 1
            yield potential_clip

    def nextClip(self):
        for potential_clip in self._nextClip():
            self.checked_clips += 1
            clip = self._checkCandidate(potential_clip)
            if clip:
                logger.info(
                    'Returning clip %s out of %s', self.checked_clips, self.total_clips)
                return clip
            else:
                continue
        logger.debug('Done with tracker %s', self)
        return None


class FixedLength(object):
    @property
    def length(self):
        return sum(c.duration for c in self.clips)


class InOrder(SegmentTracker, FixedLength):
    def getRows(self):
        return []

    def nextClip(self):
        row = self.current_row
        self.current_row += 1
        return self.clips[row] if row < len(self.clips) else None


class ExistingSegmentTracker(InOrder):
    def __init__(self, filepath, project, ratings):
        SegmentTracker.__init__(self, filepath, project, ratings)
        self.current_row = 0
        self.clips = sorted(
            [c for c in self.getClips() if c.active], key=lambda c: c.start)


class AllExistingSegmentTracker(InOrder):
    def __init__(self, filepath, project, ratings):
        SegmentTracker.__init__(self, filepath, project, ratings)
        self.current_row = 0
        self.clips = sorted([self.getClips()], key=lambda c: c.start)


class RandomExistingSegmentTracker(ExistingSegmentTracker):
    def __init__(self, filepath, project, ratings):
        ExistingSegmentTracker.__init__(self, filepath, project, ratings)
        random.shuffle(self.clips)


class PriorityRandomSegmentTracker(SegmentTracker):
    def __init__(self, filepath, project, ratings):
        SegmentTracker.__init__(self, filepath, project, ratings)
        self.priority_rows = collections.defaultdict(list)
        for row in self.rows:
            self.priority_rows[row.priority].append(row)

    def _nextClip(self):
        for priority, rows in sorted(self.priority_rows.items()):
            while rows:
                i = random.randint(0, len(rows) - 1)
                yield rows.pop(i)


class RandomSegmentTracker(SegmentTracker):
    def _nextClip(self):
        while self.rows:
            i = random.randint(0, len(self.rows)-1)
            yield self.rows.pop(i)


class CountSegmentTracker(RandomSegmentTracker):
    def __init__(self, filepath, project, ratings, n):
        self.n = n
        SegmentTracker.__init__(self, filepath, project, ratings)

    def getRows(self):
        pornfile = self.filepath.pornfile
        logger.debug('Getting Rows for %s', self)

        # first load up the existing clips
        rows = [PotentialClip(c.start, c.end, 0) for c in
                sorted(self.getClips(), key=lambda clip: clip.start)]

        if len(rows) < self.n:
            self.addRowsUniform(rows, count=self.n)
            logger.debug('Done getting rows for %s', self)
            return rows
        else:
            logger.debug('%s is already done.  Returning empty rows', self)
            return []


def segmentClips(segment_tracker):
    before = []
    pre = []
    cumshot = []
    post = []
    cumshot_found = False
    project_clips = [c for c in segment_tracker]
    for clip in sorted(project_clips, key=lambda x: x.start):
        is_cumshot = 'cumshot' in [t.tag for t in clip.tags]
        is_postcumshot = 'post.cumshot' in [t.tag for t in clip.tags]
        is_precumshot = 'pre.cumshot' in [t.tag for t in clip.tags]
        if is_cumshot:
            cumshot_found = True
        if not clip.active:
            continue
        if is_cumshot:
            cumshot.append(clip)
        elif is_precumshot:
            pre.append(clip)
        elif is_postcumshot:
            post.append(clip)
        else:
            if cumshot_found:
                post.append(clip)
            else:
                before.append(clip)
    return before, pre, cumshot, post
