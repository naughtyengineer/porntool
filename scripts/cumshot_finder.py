# Almost identical to replay_porn, but only for movies that don't
# have a clip with a 'cumshot' tag.  The tag doesn't have to be
# on an active clip.

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
from porntool import select
from porntool import tables as t
from porntool import util
from porntool import widget
from porntool.replay_porn import *

class ExcludeClipTag(filepath):
    def __init__(self, project, clip_tag):
        self.project = project
        self.clip_tag = clip_tag

    def __call__(self, filepath):
        for clip in filepath.pornfile._clips:
            if clip.project_id == self.project.id_:
                for tag in clip.tags:
                    if tag.tag == self.clip_tag:
                        return False
        return True


class OneSegmentTracker(segment.SegmentTracker):
    def __init__(self, filepath, project, *args):
        self.filepath = filepath
        self.project = project
        self.triggered = False

    def nextClip(self):
        if self.triggered:
            return None
        else:
            self.triggered = True
            start = max(0, self.filepath.pornfile.length - 60)
            return self._makeClip(
                file_id=self.filepath.file_id, project_id=self.project.id_,
                start=start, duration=10)


class Picker(clippicker.Random, clippicker.ClipPicker):
    pass


parser = argparse.ArgumentParser(
    description='Play clips for porn collection', parents=[filters.PARSER])
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=util.flexibleBoolean, help='shuffle file list')
parser.add_argument('--update-library', action='store_true', default=False)
parser.add_argument('--extra', default='')
parser.add_argument('--clip-tag', default='cumshot')
ARGS = parser.parse_args()


try:
    script.standardSetup()
    logging.info('****** Starting new script ********')

    cmd_line_files = [f.decode('utf-8') for f in ARGS.files]
    if ARGS.update_library:
        filepaths = movie.loadFiles(cmd_line_files, add_movie=movie.addMovie)
    else:
        filepaths = movie.queryFiles(cmd_line_files)
    logging.debug('filepaths: %s', len(filepaths))
    db.getSession().commit()
    logging.debug('%s files loaded', len(filepaths))

    PROJECT = t.Project(id_=1, name='redhead')

    all_filters = [
        filters.ExcludeTags(['pmv', 'cock.hero', 'compilation']),
        ExcludeClipTag(PROJECT, ARGS.clip_tag)
    ]
    all_filters.extend(filters.applyArgs(ARGS, db.getSession()))

    inventory = movie.MovieInventory(filepaths, ARGS.shuffle, all_filters)

    iinventory = inventoryFilter(inventory)

    normalratings = rating.NormalRatings(db.getSession())

    clip_picker = Picker(iinventory, PROJECT, normalratings, 20, OneSegmentTracker)

    FILL = widget.Status(valign='bottom')

    # bold is needed for the AdjustController
    palette = [('bold', 'default,bold', 'default', 'bold'),]
    CLIP_PLAYER = ClipPlayer(clip_picker, FILL, PROJECT, ARGS.extra, False)
    LOOP = urwid.MainLoop(
        FILL, palette=palette, unhandled_input=CLIP_PLAYER.handleKey, handle_mouse=False)
    CLIP_PLAYER.setLoop(LOOP)

    LOOP.set_alarm_in(1, CLIP_PLAYER.playNextClip)

    LOOP.run()
finally:
    script.standardCleanup()
    #CLIP_PLAYER.printSkippedFiles()
    logging.info('****** End of Script *********')
