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

parser = argparse.ArgumentParser(description='Tag your porn collection')
parser.add_argument('files', nargs='*', help='files to tag')
args = parser.parse_args()

script.standardSetup()

filepaths = movie.loadFiles(args.files)
db.getSession().commit()

inventory = movie.MovieInventory(filepaths, False)

def editMovie(filepath):
    main = menu.FileMenuPadding(filepath, NORMALRATINGS)
    urwid.connect_signal(main, 'done', nextMovie)
    loop.widget = urwid.Overlay(
        main, urwid.SolidFill(), align='left', width=('relative', 90),
        valign='bottom', height=('relative', 100), min_width=20, min_height=7)

script.standardCleanup()
