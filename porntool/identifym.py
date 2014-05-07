import logging
import re
import subprocess

from porntool import configure
from porntool import util

logger = logging.getLogger(__name__)

def identify(filename):
    logger.debug('Calling `identify` on %s', filename)
    p = subprocess.Popen(
        [configure.get('MPLAYER'), "--vo=null", "--ao=null", "--identify",
         "--frames=0", filename],
        stdout=subprocess.PIPE, stderr=util.DEVNULL)
    (out, err) = p.communicate()
    out = out.decode('utf-8')
    return out

class Identify(object):
    def __init__(self, output):
        self.output = output
        self._parseOutput()

    def _parseOutput(self):
        out = self.output
        video_height_m = re.search("ID_VIDEO_HEIGHT=(\d*)", out)
        video_width_m = re.search("ID_VIDEO_WIDTH=(\d*)", out)
        self.height = float(video_height_m.groups()[0])
        self.width = float(video_width_m.groups()[0])

        seekable = re.search("ID_SEEKABLE=(\d*)", out)
        self.seekable = True if seekable.groups()[0] == '1' else False

        self.length = float(re.search("ID_LENGTH=([\d\.]*)", out).groups()[0])

        for line in out.split('\n'):
            m = re.search("ID_(\w)=([^\s]+)", line)
            if m:
                setattr(self, m.group(1).lower(), m.group(2))

    @classmethod
    def load(cls, filename):
        out = identify(filename)
        return cls(out)
