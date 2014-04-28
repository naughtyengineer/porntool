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
    def __init__(self, filepath, ratings):
        self.filepath = filepath
        self.ratings = ratings
        self.rows = self.getRows()
        self.total_clips = len(self.rows)
        self.checked_clips = 0
        self.current_row = 0

    def __str__(self):
        return  u'{}<{}>'.format(self.__class__.__name__, self.filepath.path)

    def length(self):
        return random.choice([2, 2, 2, 2, 3, 3, 3, 4, 4, 5, 6, 7, 8])

    def checkedDuration(self):
        dur = sum(c.duration for c in self.filepath.pornfile.clips)
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

    def traverseGaps(self, rows, start, movie_end):
        """
        `start` is in 'gap terms', not absolute terms. so, if start
        is 10 seconds - it means ten seconds worth of gap if the
        first minute is already in `rows`, then the start would
        actually be 1:10.

        return: (location in absolute terms, remaining duration in the current gap)
        """
        if not rows:
            return start, movie_end - start
        total_gaps = 0
        last_end = 0
        gap_found = False
        for pc in rows:
            current_gap = pc.start - last_end
            if total_gaps <= start < (total_gaps + current_gap):
                # the target location is in this gap!
                gap_found = True
                break
            total_gaps += current_gap
            last_end = pc.end
        location = last_end + (start - total_gaps)
        if gap_found:
            remaining = pc.start - location
        else:
            remaining = movie_end - location
        return location, remaining

    def addRowsByFlag(self, rows):
        pornfile = self.filepath.pornfile
        flags = db.getSession().query(t.Flag).filter(
            t.Flag.file_id==pornfile.id_).all()
        # with a flag, we want to do +/- 5 around it, split randomlyish
        for flag in flags:
            start = flag.location - 5
            while start < flag.location + 5:
                end = start + self.length()
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
                target_length = self.length()
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
            def condCheck():
                return len(rows) < count
        else:
            raise Exception('either target_fraction or count must be specified')

        # failed count is largely to catch small files that fill up
        failed_count = 0
        while condCheck() and failed_count < 10:
            start = round(random.random() * (pornfile.length - duration), 1)
            location, remaining = self.traverseGaps(rows, start, pornfile.length)
            if remaining < 1.5:
                failed_count += 1
                continue
            length = min(remaining, self.length())
            end = location + length
            # don't need to check this, know its in a gap
            rows.append(PotentialClip(location, end, 2))
            rows.sort()
            duration += length

    def getRows(self):
        pornfile = self.filepath.pornfile
        logger.debug('Getting Rows for %s', self)

        # first load up the existing clips
        rows = [PotentialClip(c.start, c.end, 0) for c in
                sorted(pornfile.clips, key=lambda clip: clip.start)]

        self.addRowsByFlag(rows)
        self.addRowsByScrubs(rows)

        rating = self.ratings.getRating(pornfile)
        target_fraction = .04 * rating
        self.addRowsUniform(rows, target_fraction)

        logger.debug('Done getting rows for %s', self)
        return rows

    def _checkCandidate(self, potential_clip):
        start = potential_clip.start
        end = potential_clip.end
        overlap_found = False
        existing_clips = self.filepath.pornfile.clips
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
        clip = t.Clip(file_id=self.filepath.file_id, start=start, duration=end-start)
        db.getSession().add(clip)
        db.getSession().flush()
        return clip

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


class ExistingSegmentTracker(SegmentTracker):
    def __init__(self, filepath, ratings):
        SegmentTracker.__init__(self, filepath, ratings)
        self.current_row = 0
        self.clips = sorted(
            [c for c in self.filepath.pornfile.clips if c.active],
            key=lambda c: c.start)

    def getRows(self):
        return []

    def nextClip(self):
        row = self.current_row
        self.current_row += 1
        return self.clips[row] if row < len(self.clips) else None


class RandomExistingSegmentTracker(ExistingSegmentTracker):
    def __init__(self, filepath, ratings):
        ExistingSegmentTracker.__init__(self, filepath, ratings)
        random.shuffle(self.clips)


class PriorityRandomSegmentTracker(SegmentTracker):
    def __init__(self, filepath, ratings):
        SegmentTracker.__init__(self, filepath, ratings)
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
    def __init__(self, filepath, ratings, n):
        self.n = n
        SegmentTracker.__init__(self, filepath, ratings)

    def getRows(self):
        pornfile = self.filepath.pornfile
        logger.debug('Getting Rows for %s', self)

        # first load up the existing clips
        rows = [PotentialClip(c.start, c.end, 0) for c in
                sorted(pornfile.clips, key=lambda clip: clip.start)]

        self.addRowsUniform(rows, count=self.n)

        logger.debug('Done getting rows for %s', self)
        return rows
