import logging

import urwid

logger = logging.getLogger(__name__)

class OnFinished(object):
    def __init__(self, *args, **kwds):
        self._on_finished = []

    def addFinishedHandler(self, handler, **kwds):
        self._on_finished.append((handler, kwds))

    def onFinished(self, **kwds):
        # the *args is necessary here because sometimes onFinished will cascade
        for onf, new_kwds in self._on_finished:
            kwds.update(new_kwds)
            if hasattr(self, '_loop'):
                self._loop.alarm(0, lambda: onf(**kwds))
            else:
                onf(**kwds)

class LoopAware(object):
    def __init__(self, *args, **kwds):
        logger.debug('Initing loop aware')
        self._loop = None

    def setLoop(self, loop):
        logger.debug('Setting loop to %s', loop)
        self._loop = loop

class Status(urwid.Filler):
    def __init__(self, *args, **kwds):
        self._status = urwid.Text('')
        super(Status, self).__init__(body=self._status, *args, **kwds)

    def setStatus(self, new_status):
        self._status.set_text(new_status)
