import logging

import urwid

from porntool import adjuster
from porntool import widget

logger = logging.getLogger(__name__)


class UrwidReviewWidget(widget.Status):
    def __init__(self, *args, **kwds):
        super(UrwidReviewWidget, self).__init__(*args, **kwds)
        self._tag_editor = None

    def activateTagEditor(self, starting_tags):
        self._tag_editor = urwid.Edit('Tags: ', starting_tags)
        self.original_widget = self._tag_editor

    def deactivateTagEditor(self):
        tags = self._tag_editor.edit_text
        self._tag_editor = None
        self.original_widget = self._status
        return tags

    def isTagEditorActive(self):
        return self._tag_editor

    def keypress(self, size, key):
        if self._tag_editor:
            logger.debug('%s %s', size, key)
            super(UrwidReviewWidget, self).keypress(size, key)


class ReviewController(object):
    def __init__(self, player, review_widget, onDeactivate=None, onSave=None, *args, **kwds):
        self.review_widget = review_widget
        self._active = False
        self.player = player
        self._onDeactivate = onDeactivate
        self._onSave = onSave

    def isActive(self):
        return self._active

    def activate(self, bounds=None):
        self._active = True
        logger.debug('Reviewer Activated')
        self.player.pause()
        if not bounds:
            current = self.player.getTime()
            self.left = current - 3
            self.right = current + 1
        else:
            self.left = bounds.start
            self.right = bounds.end
        self.review_widget.setStatus('Start: {}, End: {}'.format(self.left, self.right))
        self.adjuster = None
        self.side = None
        self.tag_editor = None
        self.tags = []

    def deactivate(self):
        self.player.pause()
        self._active = False
        if self._onDeactivate:
            self._onDeactivate()

    def consume(self, key):
        if not self.isActive():
            return False
        if self.review_widget.isTagEditorActive():
            if key == 'enter':
                self.tags = self.review_widget.deactivateTagEditor()
                logger.debug('Saving tags: %s', self.tags)
            else:
                raise Exception('Surprise!')
                #self.review_widget.keypress(key)
        elif key == ' ':
            if self.player.isPaused():
                self.player.seekAndPlay(self.left, end=self.right)
            else:
                self.player.pause()
        elif key == 'l':
            self.player.pause()
            self.editLeftBoundry()
        elif key == 'r':
            self.player.pause()
            self.editRightBoundry()
        elif key == 's':
            self.player.pause()
            self.saveClip()
            self.deactivate()
        elif key == 'd':
            self.deactivate()
        elif key == 't':
            # TAG EDIT MODE
            self.review_widget.activateTagEditor('doggy anal')
        elif self.adjuster:
            if self.adjuster.consume(key):
                self.adjustBoundry()
            else:
                return False
        else:
            return False
        return True

    def saveClip(self):
        if self._onSave:
            self._onSave(self.left, self.right, self.tags)
        logger.debug('Saving!')

    def adjustBoundry(self):
        self.player.seek(self.adjuster.current_position)
        if self.side == 'left':
            self.left = self.adjuster.current_position
            if self.left >= self.right:
                self.right = self.left + 0.1
        elif self.side == 'right':
            self.right = self.adjuster.current_position
            if self.left >= self.right:
                self.left = self.right - 0.1
        self.review_widget.setStatus('Start: {}, End: {}'.format(self.left, self.right))

    def editLeftBoundry(self):
        self.adjuster = adjuster.FineAdjuster(self.left)
        self.side = 'left'

    def editRightBoundry(self):
        self.adjuster = adjuster.FineAdjuster(self.right)
        self.side = 'right'
