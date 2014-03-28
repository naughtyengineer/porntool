import argparse
import collections as cols
import itertools as it
import logging
import os.path
import random

import sqlalchemy as sql
import urwid

import porntool as pt
from porntool import controller
from porntool import db
from porntool import filters
from porntool import menu
from porntool import movie
from porntool import player
from porntool import rating
from porntool import reviewer
from porntool import script
from porntool import tables as t
from porntool import util
from porntool import widget


PotentialClip = cols.namedtuple('PotentialClip', ['start', 'end', 'priority'])


def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')


def isNotNewFilter():
    new_filter = filters.ByCount(db.getSession(), 0)
    def notNew(x):
        return not new_filter(x)
    return notNew


def is1080(filepath):
    mp = player.MoviePlayer(filepath)
    mp.identify()
    return mp.height > 720 or mp.width > 1280


def inventory_filter(inventory):
    # a function for filters specific to this script
    # that aren't worth adding to filter module
    for fp in inventory:
        # if fp.path.find('empornium') >= 0:
        #     continue
        logging.debug('Checking %s', fp)
        if os.path.splitext(fp.path)[1] != '.mp4':
            logging.debug('Skipping %s: not an mp4 file', fp)
            continue
        if is1080(fp):
            logging.debug('Skipping %s:  too high def', fp)
            continue
        if not ARGS.type == 'existing':
            if sum(c.duration for c in fp.pornfile.clips if c.active) > 180:
                logging.debug('Skipping %s because we have enough clips', fp)
                continue
        # a bit of a hack, sorry
        movie.updateMissingProperties(fp)
        yield fp


def handleKey(key):
    key = key.lower()
    logging.debug("'%s' was pressed", key)
    if CONTROLLER:
        CONTROLLER.consume(key)


def adjustClip(clip_menu):
    global CONTROLLER
    clip = clip_menu.clip
    LOOP.widget = FILL
    CONTROLLER = controller.AdjustController(clip, FILL)
    CONTROLLER.setLoop(LOOP.event_loop)
    CONTROLLER.addFinishedHandler(editClip, clip=clip)
    CONTROLLER.start()
    CONTROLLER.player.communicate('volume 10 1')


def editClip(clip):
    logging.debug('Starting editClip')
    main = menu.ClipMenuPadding(clip, adjustClip)
    main.setLoop(LOOP.event_loop)
    main.addFinishedHandler(next_clip.playNextClip, fmp=main)
    LOOP.widget = urwid.Overlay(
        main, urwid.SolidFill(), align='left', width=('relative', 90),
        valign='bottom', height=('relative', 100), min_width=20, min_height=7)


class SegmentTracker(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.rows = self.getRows()
        self.total_clips = len(self.rows)
        self.checked_clips = 0

    def __str__(self):
        return  u'{}<{}>'.format(self.__class__.__name__, self.filepath.path)

    def length(self):
        return random.choice([2, 2, 2, 2, 3, 3, 3, 4, 4, 5, 6, 7, 8])

    def checkedDuration(self):
        dur = sum(c.duration for c in self.filepath.pornfile.clips)
        #logging.debug("Duration for %s: %s", self, dur)
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
        gaps = 0
        last_end = 0
        for pc in rows:
            gap = pc.start - last_end
            if gaps <= start and gaps + gap > start:
                # the target location is in this gap!
                break
            gaps += gap
            last_end = pc.end
        location = last_end + (start - gaps)
        if pc.start > location:
            remaining = pc.start - location
        else:
            remaining = movie_end - location
        return location, remaining

    def getRows(self):
        logging.debug('Getting Rows for %s', self)
        pornfile = self.filepath.pornfile

        # first load up the existing clips
        rows = [PotentialClip(c.start, c.end, 0) for c in
                sorted(pornfile.clips, key=lambda clip: clip.start)]

        # get the flags
        flags = db.getSession().query(t.Flag).filter(
            t.Flag.file_id==pornfile.id_).all()
        # with a flag, we want to do +/- 5 around it, split randomlyish
        for flag in flags:
            start = flag.location - 5
            while start < flag.location + 5:
                end = start + self.length()
                self.addRow(rows, start, end, 0)
                start = end

        # get the scrubs
        query = sql.select(
            [t.Scrub.c.start, t.Scrub.c.end]
        ).select_from(
            t.Scrub
        ).where(
            t.Scrub.c.file_id == pornfile.id_)
        scrubs = sorted([(s, e) for s,e in db.getSession().execute(query).fetchall()])
        last_end = 0
        for potential_clip in rows:
            start = potential_clip.start
            end = potential_clip.end
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

        rating = NORMALRATINGS.getRating(pornfile)
        target_fraction = .04 * rating
        # fill in gaps to get to get the target_fraction:
        duration = sum(pc.end - pc.start for pc in rows)
        logging.info(
            'Rating: %s; target fraction: %s; current fraction: %s',
            rating, target_fraction, duration / pornfile.length)

        while duration / pornfile.length < target_fraction:
            start = round(random.random() * (pornfile.length - duration), 1)
            location, remaining = self.traverseGaps(rows, start, pornfile.length)
            length = min(remaining, self.length())
            if length < 1.5:
                continue
            end = location + length
            # don't need to check this, know its in a gap
            rows.append(PotentialClip(location, end, 2))
            rows.sort()
            duration += length
        logging.debug('Done getting rows for %s', self)
        return rows

    def _checkCandidate(self, potential_clip):
        start = potential_clip.start
        end = potential_clip.end
        overlap_found = False
        existing_clips = self.filepath.pornfile.clips
        for eclip in existing_clips:
            if eclip.start <= start and start <= eclip.end:
                overlap_found = True
                break
            if eclip.start <=end and end <= eclip.end:
                overlap_found = True
                break
        if overlap_found:
            logging.debug('Overlap found.  Skipping')
            return None
        clip = t.Clip(file_id=self.filepath.file_id, start=start, duration=end-start)
        db.getSession().add(clip)
        db.getSession().flush()
        return clip

    def _nextClip(self):
        self.current_row = 0
        while self.current_row < len(self.rows):
            logging.debug("Current Row: %s", self.current_row)
            start, end = self.rows[self.current_row]
            self.current_row += 1
            yield start, end

    def nextClip(self):
        for potential_clip in self._nextClip():
            self.checked_clips += 1
            clip = self._checkCandidate(potential_clip)
            if clip:
                logging.info('Returning clip %s out of %s', self.checked_clips, self.total_clips)
                return clip
            else:
                continue
        logging.debug('Done with tracker %s', self)
        return None


class ExistingSegmentTracker(SegmentTracker):
    def __init__(self, filepath):
        SegmentTracker.__init__(self, filepath)
        self.current_row = 0
        self.clips = sorted(
            [c for c in self.filepath.pornfile.clips if c.active],
            key=lambda c: c.start)

    def nextClip(self):
        row = self.current_row
        self.current_row += 1
        return self.clips[row] if row < len(self.clips) else None

class RandomExistingSegmentTracker(ExistingSegmentTracker):
    def __init__(self, filepath):
        ExistingSegmentTracker.__init__(self, filepath)
        random.shuffle(self.clips)


class PriorityRandomSegmentTracker(SegmentTracker):
    def __init__(self, filepath):
        SegmentTracker.__init__(self, filepath)
        self.priority_rows = cols.defaultdict(list)
        for row in self.rows:
            self.priority_rows[row[2]].append(row)

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

class NextClip(object):
    def __init__(self, iinventory, n=20, tracker_factory=None):
        self.iinventory = inventory_filter(iinventory)
        self.tracker_factory = tracker_factory or PriorityRandomSegmentTracker
        self.trackers = []
        self.addTrackers(n)
        self.current_tracker = None

    def _newTracker(self):
        fp = next(self.iinventory)
        s = self.tracker_factory(fp)
        return s

    def addTrackers(self, n=1):
        for _ in range(n):
            try:
                self.trackers.append(self._newTracker())
            except StopIteration:
                break

    def removeTracker(self, tracker):
        logging.debug('Removing tracker: %s', tracker)
        self.trackers.remove(tracker)
        try:
            t = self._newTracker()
            logging.debug('Adding tracker: %s', t)
            self.trackers.append(t)
        except StopIteration:
            pass

    def _nextTracker(self):
        return min(self.trackers, key=lambda t: t.checkedDuration())

    def getNextClip(self):
        if not self.trackers:
            logging.debug('Exiting!')
            raise urwid.ExitMainLoop()
        #tracker = random.choice(self.trackers)
        tracker = self._nextTracker()
        self.current_tracker = tracker
        logging.debug('Switching to %s', tracker)
        clip = tracker.nextClip()
        if not clip:
            self.removeTracker(tracker)
            return self.getNextClip()
        return clip

    def setupController(self, clip):
        global CONTROLLER
        filepath = clip.moviefile.getActivePath()
        CONTROLLER = controller.BaseController(filepath, FILL)
        CONTROLLER.setLoop(LOOP.event_loop)
        CONTROLLER.player.save_scrub = False
        LOOP.widget = FILL
        CONTROLLER.start()
        def finish():
            CONTROLLER.player.quit()
            if ARGS.no_edit:
                self.playNextClip()
            else:
                editClip(clip)
        CONTROLLER.player.communicate('volume 10 1')
        CONTROLLER.player.seekAndPlay(
            start=clip.start, duration=clip.duration, onFinished=finish)

    def playNextClip(self, fmp=None, *args):
        # first, process the last one, if need be
        if fmp:
            if hasattr(fmp, 'keep'):
                if fmp.keep:
                    logging.debug('Keeping clip')
                    fmp.clip.active = 1
                else:
                    logging.debug('Deleting clip')
                    fmp.clip.active = 0
                db.getSession().commit()
            if hasattr(fmp, 'skip') and fmp.skip:
                db.getSession().delete(fmp.clip)
                self.removeTracker(self.current_tracker)
            if hasattr(fmp, 'add') and fmp.add:
                self.addTrackers()
        try:
            same_movie = fmp and fmp.same_movie
        except:
            same_movie = False
        if same_movie:
            clip = fmp.clip
        else:
            clip = self.getNextClip()
        self.setupController(clip)


class RandomNextClip(NextClip):
    def _nextTracker(self):
        return random.choice(self.trackers)

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=flexibleBoolean)
parser.add_argument(
    '-n', '--nfiles', default=20, type=int, help='number of files to rotate through')
parser.add_argument('--type', choices=('new', 'existing'), default='new')
parser.add_argument('--no_edit', action='store_true', default=False)
parser.add_argument('--tracker', choices=('least', 'shuffle'), default='least')
parser.add_argument('--update_library', action='store_true', default=False)
ARGS = parser.parse_args()

try:
    script.standardSetup()
    logging.info('****** Starting new script ********')

    if ARGS.update_library:
        filepaths = movie.loadFiles(ARGS.files)
    else:
        uniq_filepaths = {}
        for file_ in ARGS.files:
            some_filepaths = db.getSession().query(t.FilePath).filter(
                (t.FilePath.hostname == util.hostname) &
                (t.FilePath.path.like('{}%'.format(file_)))
            ).all()
            uniq_filepaths.update({fp.file_id: fp for fp in some_filepaths})
        filepaths = uniq_filepaths.values()
    db.getSession().commit()

    inventory = movie.MovieInventory(
        filepaths, ARGS.shuffle,
        [filters.exists, isNotNewFilter(), filters.ExcludeTags(['pmv', 'cock.hero'])])

    iinventory = (inventory)

    NORMALRATINGS = rating.NormalRatings(db.getSession())
    CONTROLLER = None

    if ARGS.type == 'new':
        if ARGS.tracker == 'least':
            next_clip = NextClip(iinventory, ARGS.nfiles)
        elif ARGS.tracker == 'shuffle':
            next_clip = RandomNextClip(iinventory, ARGS.nfiles)
    elif ARGS.type == 'existing':
        next_clip = RandomNextClip(iinventory, ARGS.nfiles, RandomExistingSegmentTracker)
    #FILL = reviewer.UrwidReviewWidget(valign='bottom')
    FILL = widget.Status(valign='bottom')

    # bold is needed for the AdjustController
    palette = [('bold', 'default,bold', 'default', 'bold'),]
    LOOP = urwid.MainLoop(FILL, palette=palette, unhandled_input=handleKey)

    LOOP.set_alarm_in(1, next_clip.playNextClip)

    LOOP.run()
finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
