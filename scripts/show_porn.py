import argparse
import logging

import urwid

import porntool as pt
from porntool import controller
from porntool import db
from porntool import movie
from porntool import player
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
args = parser.parse_args()

script.standardSetup()

filepaths = movie.loadFiles(args.files)
db.getSession().commit()

inventory = movie.MovieInventory(filepaths, args.shuffle)
iinventory = iter(inventory)

CONTROLLER = None

def handleKey(key):
    key = key.lower()
    logging.debug("'%s' was pressed", key)
    if CONTROLLER:
        CONTROLLER.consume(key)

def nextMovie(*args):
    global CONTROLLER
    db.getSession().commit()
    try:
        filepath = next(iinventory)
        CONTROLLER = controller.FlagController(filepath, fill)
        CONTROLLER.addFinishedHandler(nextMovie)
        CONTROLLER.setLoop(loop)
        CONTROLLER.start()
    except StopIteration:
        logging.debug('Exiting!')
        raise urwid.ExitMainLoop()

#filepath = next(iinventory)

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
