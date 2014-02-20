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

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--shuffle', default=True, type=flexibleBoolean)
parser.add_argument('--playcount', type=int)
args = parser.parse_args()

script.standardSetup()

filepaths = movie.loadFiles(args.files)
db.getSession().commit()

if args.playcount is not None:
    count_filter = filters.ByCount(db.getSession(), args.playcount)
else:
    count_filter = None

inventory = movie.MovieInventory(
    filepaths, args.shuffle, [filters.exists, count_filter])
iinventory = iter(inventory)

NORMALRATINGS = rating.NormalRatings(db.getSession())
CONTROLLER = None

def handleKey(key):
    key = key.lower()
    logging.debug("'%s' was pressed", key)
    if CONTROLLER:
        CONTROLLER.consume(key)

def editMovie(filepath):
    # first, save a usage instance
    db.saveUsage(filepath.pornfile, CONTROLLER.player.playtime)
    db.getSession().commit()

    main = menu.FileMenuPadding(filepath, NORMALRATINGS)
    urwid.connect_signal(main, 'done', nextMovie)
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
        CONTROLLER.addFinishedHandler(editMovie, filepath)
        CONTROLLER.setLoop(loop.event_loop)
        loop.widget = fill
        CONTROLLER.start()
    except StopIteration:
        logging.debug('Exiting!')
        raise urwid.ExitMainLoop()
    finally:
        db.getSession().commit()


fill = reviewer.UrwidReviewWidget(valign='bottom')
#scout = controller.ScoutController(filepath, fill)
#scout.addFinishedHandler(exit)

loop = urwid.MainLoop(fill, unhandled_input=handleKey)

#scout.setLoop(loop)

loop.set_alarm_in(1, nextMovie)
loop.run()

db.getSession().commit()

# fill = reviewer.UrwidReviewWidget('bottom')
# scout = controller.ScoutController(filepath, player, fill)

# loop = urwid.MainLoop(fill, unhandled_input=show_or_exit)
# player.setLoop(loop)
# loop.set_alarm_in(1, scout.start)
# loop.run()


# for filepath in inventory:
#     sp = player.SlavePlayer(filepath.play)

#     q = raw_input('Enter to continue: ')

#osascript -e 'tell application "Terminal"
#    tell window 1
#        set size to {1440, 190}
#        set position to {0, 705}
#    end tell
#end tell'
