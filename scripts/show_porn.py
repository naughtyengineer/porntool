import argparse
import logging

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

def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')

def handleKey(key):
    if CONTROLLER:
        CONTROLLER.consume(key)

def editMovie(filepath):
    # first, save a usage instance
    db.saveUsage(filepath.pornfile, CONTROLLER.player.playtime)
    db.getSession().commit()

    main = menu.FileMenuPadding(filepath, NORMALRATINGS)
    main.addFinishedHandler(nextMovie, fmp=main)
    main.setLoop(loop.event_loop)
    loop.widget = urwid.Overlay(
        main, urwid.SolidFill(), align='left', width=('relative', 90),
        valign='bottom', height=('relative', 100), min_width=20, min_height=7)

def nextMovie(fmp=None, *args):
    global CONTROLLER
    try:
        try:
            if fmp.same_movie:
                filepath = fmp.filepath
            else:
                filepath = next(iinventory)
        except:
            filepath = next(iinventory)
        CONTROLLER = controller.FlagController(filepath, fill)
        CONTROLLER.addFinishedHandler(editMovie, filepath=filepath)
        CONTROLLER.setLoop(loop.event_loop)
        loop.widget = fill
        CONTROLLER.start()
    except StopIteration:
        logging.debug('Exiting!')
        raise urwid.ExitMainLoop()
    finally:
        db.getSession().commit()

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=flexibleBoolean)
parser.add_argument('--max-count', type=int)
parser.add_argument('--min-count', type=int)
parser.add_argument('--include_tags', nargs="+")
parser.add_argument('--exclude_tags', nargs="+")
args = parser.parse_args()

script.standardSetup()

try:
    filepaths = movie.loadFiles(args.files, add_movie=movie.addMovie)
    db.getSession().commit()

    all_filters = [filters.Exists()]

    if args.min_count is not None:
        all_filters.append(filters.ByMinCount(db.getSession(), args.min_count))

    if args.max_count is not None:
        all_filters.append(filters.ByMaxCount(db.getSession(), args.max_count))

    if args.include_tags:
        all_filters.append(filters.IncludeTags(args.include_tags))

    if args.exclude_tags:
        all_filters.append(filters.ExcludeTags(args.exclude_tags))

    inventory = movie.MovieInventory(filepaths, args.shuffle, all_filters)
    iinventory = iter(inventory)

    NORMALRATINGS = rating.NormalRatings(db.getSession())
    CONTROLLER = None

    fill = reviewer.UrwidReviewWidget(valign='bottom')
    loop = urwid.MainLoop(fill, unhandled_input=handleKey)

    loop.set_alarm_in(1, nextMovie)
    loop.run()
finally:
    db.getSession().commit()
    script.standardCleanup()
