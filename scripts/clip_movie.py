import argparse
import logging

import urwid

from porntool import util
from porntool import db
from porntool import reviewer
from porntool import configure
from porntool import controller
from porntool import script
from porntool import movie

parser = argparse.ArgumentParser()
parser.add_argument('filename')
ARGS = parser.parse_args()

script.standardSetup()


def handleKey(key):
    key = key.lower()
    logging.debug("'%s' was pressed", key)
    scout.consume(key)

def exit():
    logging.debug('Exiting!')
    raise urwid.ExitMainLoop()

filepath = movie.getMovie(ARGS.filename)
db.getSession().commit()

fill = reviewer.UrwidReviewWidget(valign='bottom')
scout = controller.ScoutController(filepath, fill)
scout.addFinishedHandler(exit)

loop = urwid.MainLoop(fill, unhandled_input=handleKey)
scout.setLoop(loop)
loop.set_alarm_in(1, scout.start)
loop.run()

db.getSession().commit()
