# The replay approach seems flawed.  I'd prefer to have a clip review
# mode where maybe, in a similar fashion as this script - clips are
# choosen from five files, but instead of playing continuously there
# is a dialog after each one asking to keep or save, along with the
# ability to add tags (like position) which would get persisted to a
# clip tag and a clip_tag table (there is already a Clip object in the
# schema - use it)

import argparse
import itertools as it
import logging
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
from porntool import widget


def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=flexibleBoolean)
args = parser.parse_args()

script.standardSetup()

filepaths = movie.loadFiles(args.files)
db.getSession().commit()

def isNotNewFilter():
    new_filter = filters.ByCount(db.getSession(), 0)
    def notNew(x):
        return not new_filter(x)
    return notNew

inventory = movie.MovieInventory(
    filepaths, args.shuffle,
    [filters.exists, isNotNewFilter(), filters.ExcludeTags(['pmv', 'cock.hero'])])

def inventory_filter(inventory):
    # a function for filters specific to this script
    # that aren't worth adding to filter module
    for i in inventory:
        if sum(c.duration for c in i.pornfile.clips if c.active) < 180:
            # a bit of a hack, sorry
            movie.updateMissingProperties(i)
            yield i
        else:
            logging.debug('Skipping %s because we have enough clips', i)

iinventory = inventory_filter(inventory)


NORMALRATINGS = rating.NormalRatings(db.getSession())
CONTROLLER = None

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
    CONTROLLER.addFinishedHandler(editClip, clip)
    CONTROLLER.start()
    CONTROLLER.player.communicate('volume 10 1')

def editClip(clip):
    main = menu.ClipMenuPadding(clip, adjustClip)
    urwid.connect_signal(main, 'done', next_clip.playNextClip)
    LOOP.widget = urwid.Overlay(
        main, urwid.SolidFill(), align='left', width=('relative', 90),
        valign='bottom', height=('relative', 100), min_width=20, min_height=7)


class SegmentTracker(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.rows = self.getRows()
        self.current_row = 0

    def __str__(self):
        return  u'{}<{}>'.format(self.__class__.__name__, self.filepath.path)

    def length(self):
        return random.choice([2, 2, 2, 2, 3, 3, 3, 4, 4, 5, 6, 7, 8])

    def checkedDuration(self):
        return sum(c.duration for c in self.filepath.pornfile.clips)

    def getRows(self):
        pornfile = self.filepath.pornfile
        query = sql.select(
            [t.Scrub.c.start, t.Scrub.c.end]
        ).select_from(
            t.Scrub
        ).where(
            t.Scrub.c.file_id == pornfile.id_)
        rows = sorted([(s, e) for s,e in db.getSession().execute(query).fetchall()])
        new_rows = []
        if not rows:
            # no scrub info exists - randomly pick 20% of the movie
            potential_clip_length = 0.0
            while potential_clip_length / pornfile.length < .2:
                start = round(random.random() * pornfile.length, 1)
                end = min(start + self.length(), pornfile.length)
                potential_clip_length += end - start
                new_rows.append((start, end))
        else:
            last_end = 0
            for start, end in rows:
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
                        new_rows.append((start, start + target_length))
                        # skip ahead some bit to make it interesting
                        start = start + target_length + random.randint(10, 20)
                    else:
                        new_rows.append((start, end))
                        break
        return new_rows

    def _checkCandidate(self, start, end):
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
        logging.debug("Current Row: %s", self.current_row)
        while self.current_row < len(self.rows):
            start, end = self.rows[self.current_row]
            self.current_row += 1
            yield start, end

    def nextClip(self):
        for start, end in self._nextClip():
            clip = self._checkCandidate(start, end)
            if clip:
                return clip
            else:
                continue
        logging.debug('Done with tracker %s', self)
        return None

class RandomSegmentTracker(SegmentTracker):
    def _nextClip(self):
        while self.rows:
            i = random.randint(0, len(self.rows)-1)
            yield self.rows.pop(i)

class NextClip(object):
    def __init__(self, iinventory, n=5):
        self.iinventory = iinventory
        self.trackers = [RandomSegmentTracker(fp) for fp in it.islice(iinventory, n)]
        self.current_tracker = None

    def _newTracker(self):
        s = RandomSegmentTracker(next(iinventory))
        return s

    def removeTracker(self, tracker):
        logging.debug('Removing tracker: %s', tracker)
        self.trackers.remove(tracker)
        try:
            t = self._newTracker()
            logging.debug('Adding tracker: %s', t)
            self.trackers.append(t)
        except StopIteration:
            pass

    def getNextClip(self):
        if not self.trackers:
            logging.debug('Exiting!')
            raise urwid.ExitMainLoop()
        #tracker = random.choice(self.trackers)
        tracker = min(self.trackers, key=lambda t: t.checkedDuration())
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
        try:
            same_movie = fmp and fmp.same_movie
        except:
            same_movie = False
        if same_movie:
            clip = fmp.clip
        else:
            clip = self.getNextClip()
        self.setupController(clip)


next_clip = NextClip(iinventory, n=40)
logging.info('****** Starting new script ********')
#FILL = reviewer.UrwidReviewWidget(valign='bottom')
FILL = widget.Status(valign='bottom')

# bold is needed for the AdjustController
palette = [('bold', 'default,bold', 'default', 'bold'),]
LOOP = urwid.MainLoop(FILL, palette=palette, unhandled_input=handleKey)

LOOP.set_alarm_in(1, next_clip.playNextClip)
try:
    LOOP.run()
finally:
    script.standardCleanup()
