import logging

from porntool import adjuster
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

    def __init__(self, filepath, status_widget, **kwds):
        self.filepath = filepath
        self.widget = status_widget
        status_widget.setStatus(filepath.path, 0)
        self.player = player.SlavePlayer(filepath, **kwds)
        self.player.addFinishedHandler(self.onFinished)
        widget.OnFinished.__init__(self)
        widget.LoopAware.__init__(self)

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


class AdjustController(BaseController):
    def __init__(self, clip, status_widget, bold_palette_name='bold', *args, **kwds):
        self.clip = clip
        self.original = (clip.start, clip.duration)
        self.bold_palette_name = bold_palette_name
        filepath = clip.moviefile.getActivePath()
        self.adjuster = None
        self.side = None
        super(AdjustController, self).__init__(filepath, status_widget, *args, **kwds)

    def start(self, *args):
        self.setStatus()
        self.player.start()
        self.player.pause()
        self.player.seek(self.clip.start)

    def consume(self, key):
        logger.debug('%s recieved key: %s', self.__class__.__name__, key)
        if key == ' ':
            if self.player.isPaused():
                self.player.seekAndPlay(self.clip.start, end=self.clip.end)
            else:
                self.player.pause()
        elif key == 'r':
            self.player.pause()
            self.reset()
        elif key == 's':
            self.player.pause()
            self.editStartBoundry()
        elif key == 'e':
            self.player.pause()
            self.editEndBoundry()
        elif self.adjuster:
            if self.adjuster.consume(key):
                self.adjustBoundry()
            else:
                return super(AdjustController, self).consume(key)
        else:
            return super(AdjustController, self).consume(key)
        return True

    def reset(self):
        self.clip.start = self.original[0]
        self.clip.duration = self.original[1]
        self.player.seek(self.clip.start)
        self.setStatus()

    def adjustBoundry(self):
        self.player.seek(self.adjuster.current_position)
        if self.side == 'start':
            self.clip.setStart(self.adjuster.current_position)
            if self.clip.end <= self.adjuster.current_position:
                self.clip.duration = 0.1
        elif self.side == 'end':
            if self.clip.start >= self.adjuster.current_position:
                self.clip.start = self.adjuster.current_position - 0.1
                self.clip.duration = 0.1
            else:
                self.clip.setEnd(self.adjuster.current_position)
        self.setStatus()

    def _isOverlap(self, time):
        project_clips = sorted(
            [c for c in self.clip.moviefile._clips
             if c.project_id == self.clip.project_id and c.active], key=lambda x: x.start)
        for clip in project_clips:
            if clip.start <= time <= clip.end:
                return True
        return False

    def setStatus(self):
        start_text = 'Start: {}'.format(self.clip.start)
        end_text = 'End: {}'.format(self.clip.end)
        if self._isOverlap(self.clip.start):
            start_text = '**' + start_text + '**, '
        else:
            start_text += ', '
        if self._isOverlap(self.clip.end):
            end_text = '**' + end_text + '**'
        if self.adjuster:
            if self.side == 'start':
                status = ['Edit: ',
                          (self.bold_palette_name, start_text),
                          end_text]
            elif self.side == 'end':
                status = ['Edit: ',
                          start_text,
                          (self.bold_palette_name, end_text)]
        else:
            status = start_text + end_text
        self.widget.setStatus(status)

    def editStartBoundry(self):
        self.adjuster = adjuster.FineAdjuster(self.clip.start)
        self.side = 'start'
        self.setStatus()

    def editEndBoundry(self):
        self.adjuster = adjuster.FineAdjuster(self.clip.end)
        self.side = 'end'
        self.setStatus()
