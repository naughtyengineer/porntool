import argparse
import collections as cols
import itertools as it
import logging
import os.path
import random

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
from porntool import script
from porntool import segment
from porntool import select
from porntool import tables as t
from porntool import util
from porntool import widget

logger = logging.getLogger(__name__)

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
        logger.debug('Checking %s', fp)
        # if os.path.splitext(fp.path)[1] != '.mp4':
        #     logger.debug('Skipping %s: not an mp4 file', fp)
        #     continue
        # if is1080(fp):
        #     logger.debug('Skipping %s:  too high def', fp)
        #     continue
        # a bit of a hack, sorry
        try:
            movie.updateMissingProperties(fp)
        except:
            logger.exception('Skipping %s. Failed to update properties.', fp)
            continue
        yield fp


class ClipPlayer(object):
    def __init__(self, clip_picker, fill, project, extra, no_edit, skip_preview=False):
        self.clip_picker = clip_picker
        self.fill = fill
        self.project = project
        self.skipped_files = []
        self.extra = extra
        self.no_edit = no_edit
        self.controller = None
        # set to True to just go straight to editing a clip
        self.skip_preview = skip_preview

    def setLoop(self, loop):
        self.loop = loop

    def _adjustClip(self, clip_menu):
        clip = clip_menu.clip
        self.loop.widget = self.fill
        self.controller = controller.AdjustController(clip, self.fill)
        self.controller.setLoop(self.loop.event_loop)
        self.controller.addFinishedHandler(self._editClip, clip=clip)
        self.controller.start()

    def _editClip(self, clip):
        logger.debug('Starting editClip')
        main = menu.ClipMenuPadding(
            clip, self.project, self._adjustClip, '({}) '.format(self.clip_picker.counter))
        main.setLoop(self.loop.event_loop)
        main.addFinishedHandler(self.playNextClip, fmp=main)
        self.loop.widget = urwid.Overlay(
            main, urwid.SolidFill(), align='left', width=('relative', 90),
            valign='bottom', height=('relative', 100), min_width=20, min_height=7)

    def handleKey(self, key):
        if self.controller:
            self.controller.consume(key)

    def setupController(self, clip):
        filepath = clip.moviefile.getActivePath()
        if self.skip_preview:
            self.controller = controller.AdjustController(clip, self.fill, extra=self.extra)
        else:
            self.controller = controller.BaseController(filepath, self.fill, extra=self.extra)
        self.controller.setLoop(self.loop.event_loop)
        self.controller.player.save_scrub = False
        self.loop.widget = self.fill # is this line necessary?
        self.controller.start()
        def finish():
            self.controller.player.quit()
            if self.no_edit:
                self.playNextClip()
            else:
                self._editClip(clip)
        if self.skip_preview:
            self.controller.addFinishedHandler(self._editClip, clip=clip)
            self.controller.start()
        else:
            self.controller.player.seekAndPlay(
                start=clip.start, duration=clip.duration, onFinished=finish)

    def playNextClip(self, fmp=None, *args):
        # first, process the last one, if need be
        if fmp:
            if hasattr(fmp, 'keep'):
                if fmp.keep:
                    logger.debug('Keeping clip')
                    fmp.clip.active = 1
                else:
                    logger.debug('Deleting clip')
                    fmp.clip.active = 0
                db.getSession().commit()
            if hasattr(fmp, 'skip') and fmp.skip:
                logger.debug('Skipping file')
                db.getSession().delete(fmp.clip)
                self.clip_picker.replaceTracker()
                self.skipped_files.append(self.clip_picker.current_tracker.filepath)
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

    def printSkippedFiles(self):
        if self.skipped_files:
            print 'You skipped these files:'
            for fp in self.skipped_files:
                print fp.path
