import logging

logger = logging.getLogger(__name__)

class AdjusterSubController(object):
    """responds to key commands to adjust a position"""
    _keymap = {}
    def __init__(self, current_position):
        self.current_position = current_position

    def consume(self, key):
        delta = self._keymap.get(key)
        if delta:
            logger.debug('Adjusting %s with key: %s', delta, key)
            self.updatePosition(delta)
            return True
        else:
            return False

    def updatePosition(self, delta):
        self.current_position += delta


class FineAdjuster(AdjusterSubController):
    _keymap = {
            ','    :  -0.1,
            'left' :  -1.0,
            'down' :  -5.0,
            '<'    : -10.0,
            '.'    :   0.1,
            'right':   1.0,
            'up'   :   5.0,
            '>'    :  10.0,
        }
