import argparse
import collections as cols
import itertools as it
import logging
import os.path
import random

import sqlalchemy as sql
import urwid

import porntool as pt
from porntool import clippicker
from porntool import controller
from porntool import db
from porntool import filters
from porntool import menu
from porntool import movie
from porntool import player
from porntool import rating
from porntool import reviewer
from porntool import script
from porntool import segment
from porntool import tables as t
from porntool import util
from porntool import widget


def is1080(filepath):
    mp = player.MoviePlayer(filepath)
    mp.identify()
    return mp.height > 720 or mp.width > 1280


def inventoryFilter(inventory):
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
    main.addFinishedHandler(clip_player.playNextClip, fmp=main)
    LOOP.widget = urwid.Overlay(
        main, urwid.SolidFill(), align='left', width=('relative', 90),
        valign='bottom', height=('relative', 100), min_width=20, min_height=7)

class ClipPlayer(object):
    def __init__(self, clip_picker):
        self.clip_picker = clip_picker

    def setupController(self, clip):
        global CONTROLLER
        filepath = clip.moviefile.getActivePath()
        CONTROLLER = controller.BaseController(filepath, FILL, extra=ARGS.extra)
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
                self.clip_picker.removeTracker()
            if hasattr(fmp, 'add') and fmp.add:
                self.clip_picker.addTrackers(fmp.add)
        try:
            same_movie = fmp and fmp.same_movie
        except:
            same_movie = False
        if same_movie:
            clip = fmp.clip
        else:
            clip = self.clip_picker.getNextClip()
            if clip is None:
                raise urwid.ExitMainLoop()
        self.setupController(clip)



segment_trackers = {
    'new': segment.PriorityRandomSegmentTracker,
    'existing': segment.ExistingSegmentTracker,
    'sample': lambda fp, n: segment.CountSegmentTracker(fp, n, 10),
}

clip_types = {
    'least': clippicker.ClipPicker,
    'shuffle': clippicker.RandomClipPicker,
    'new': clippicker.OnlyNewClips,
}

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=util.flexibleBoolean)
parser.add_argument(
    '-n', '--nfiles', default=20, type=int, help='number of files to rotate through')
parser.add_argument('--no-edit', action='store_true', default=False)
parser.add_argument('--clip-type', choices=clip_types.keys(), default='shuffle')
parser.add_argument('--tracker', choices=segment_trackers.keys(), default='sample')
parser.add_argument('--update-library', action='store_true', default=False)
parser.add_argument('--extra', default='')
ARGS = parser.parse_args()

try:
    script.standardSetup()
    logging.info('****** Starting new script ********')

    if ARGS.update_library:
        filepaths = movie.loadFiles(ARGS.files)
    else:
        filepaths = []
        for file_ in ARGS.files:
            some_filepaths = db.getSession().query(t.FilePath).filter(
                (t.FilePath.hostname == util.hostname) &
                (t.FilePath.path.like('{}%'.format(file_)))
            ).all()
            filepaths.extend(some_filepaths)
            #uniq_filepaths.update({fp.file_id: fp for fp in some_filepaths})
        #filepaths = uniq_filepaths.values()
    db.getSession().commit()

    inventory = movie.MovieInventory(
        filepaths, ARGS.shuffle,
        [filters.Exists(), filters.ByMinCount(db.getSession(), 1),
         filters.ExcludeTags(['pmv', 'cock.hero'])])

    iinventory = inventoryFilter(inventory)

    normalratings = rating.NormalRatings(db.getSession())
    CONTROLLER = None

    segment_tracker = segment_trackers[ARGS.tracker]
    clip_type = clip_types[ARGS.clip_type]
    clip_picker = clip_type(iinventory, normalratings, ARGS.nfiles, segment_tracker)
    clip_player = ClipPlayer(clip_picker)

    FILL = widget.Status(valign='bottom')

    # bold is needed for the AdjustController
    palette = [('bold', 'default,bold', 'default', 'bold'),]
    LOOP = urwid.MainLoop(FILL, palette=palette, unhandled_input=handleKey)

    LOOP.set_alarm_in(1, clip_player.playNextClip)

    LOOP.run()
finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
