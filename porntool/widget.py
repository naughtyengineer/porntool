import logging

import urwid

logger = logging.getLogger(__name__)

class OnFinished(object):
    def __init__(self, *args, **kwds):
        self._on_finished = []
        super(OnFinished, self).__init__(*args, **kwds)

    def addFinishedHandler(self, handler):
        self._on_finished.append(handler)

    def onFinished(self):
        for onf in self._on_finished:
            onf()

class LoopAware(object):
    def __init__(self, *args, **kwds):
        logger.debug('Initing loop aware')
        self._loop = None

    def setLoop(self, loop):
        self._loop = loop

class Status(urwid.Filler):
    def __init__(self, *args, **kwds):
        self._status = urwid.Text('')
        super(Status, self).__init__(body=self._status, *args, **kwds)

    def setStatus(self, new_status):
        self._status.set_text(new_status)
