import logging

from porntool import db
from porntool import player
from porntool import reviewer
from porntool import tables
from porntool import tag
from porntool import widget

logger = logging.getLogger(__name__)

class BaseController(widget.OnFinished, widget.LoopAware):
    """just plays a movie, provides standard keyboard shortcuts to navigate"""
    _keymap = {
        ','    :  -1,
        'left' : -10,
        'down' : -30,
        '<'    : -60,
        '.'    :   1,
        'right':  10,
        'up'   :  30,
        '>'    :  60,
    }

    def __init__(self, filepath, status_widget, *args, **kwds):
        super(BaseController, self).__init__(filepath, *args, **kwds)
        self.filepath = filepath
        self.widget = status_widget
        self.player = player.SlavePlayer(filepath.path)
        self.player.addFinishedHandler(self.onFinished)

    def setLoop(self, loop):
        self.player.setLoop(loop)
        super(BaseController, self).setLoop(loop)

    def start(self, *args):
        self.widget.setStatus(u'Playing {}'.format(self.filepath.path))
        self.player.start()

    def consume(self, key):
        if key == 'q':
            self.player.quit()
        elif key == ' ':
            self.player.togglePause()
        elif key == 'o':
            self.player.osd()
        elif key == '/':
            self.player.changeVolume(-1)
        elif key == '0':
            self.player.changeVolume(1)
        else:
            seek = self._keymap.get(key)
            if seek:
                self.player.seek(seek, self.player.SEEK_RELATIVE)


class FlagController(BaseController):
    """A controller that lets a user flag locations in a movie"""
    def __init__(self, *args, **kwds):
        super(FlagController, self).__init__(*args, **kwds)

    def addFlagNow(self):
        location = self.player.getTime()
        file_id = self.filepath.file_id
        flag = tables.Flag(file_id=file_id, location=location)
        db.getSession().add(flag)
        logger.debug('Adding flag at %s', location)
        self.widget.setStatus('Flag added at {}'.format(location))

    def consume(self, key):
        if key == 'f':
            self.addFlagNow()
        else:
            super(FlagController, self).consume(key)


class ScoutController(BaseController):
    """A controller that lets the user skip around to the next clip to edit"""
    def __init__(self, filepath, review_widget, *args, **kwds):
        super(ScoutController, self).__init__(filepath, review_widget, *args, **kwds)
        self.reviewer = reviewer.ReviewController(
            self.player, review_widget, self._onDeactivate, self._onSave)

    def _onDeactivate(self):
        logger.debug('Back to reviewing')
        self.widget.setStatus("Hit 'e' to enter edit mode")

    def _onSave(self, left, right, tags):
        logger.debug('Would have saved: %s, %s, %s', left, right, tags)
        tag_objects = [tag.getTag(t) for t in tags]
        clip = tables.Clip(
            file_id = self.filepath.file_id, start=left, duration=right-left, tags=tag_objects)
        db.getSession().add(clip)

    def areReviewing(self):
        return self.reviewer.isActive()

    def consume(self, key):
        if self.areReviewing():
            consumed = self.reviewer.consume(key)
            if not consumed:
                super(ScoutController, self).consume(key)
        else:
            if key == 'e':
                self.reviewer.activate()
            else:
                super(ScoutController, self).consume(key)
