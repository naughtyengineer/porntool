import logging
import re
import subprocess
import time

from porntool import async_subprocess
from porntool import configure
from porntool import widget

logger = logging.getLogger(__name__)

def parseTime(stdout):
    if stdout:
        m = re.match('ANS_TIME_POSITION=([\d\.]+)', stdout)
        if m:
            return float(m.group(1))

class MoviePlayer(object):
    def __init__(self, filename):
        self.filename = filename

    def identify(self):
        p = subprocess.Popen(
            [configure.get('MPLAYER'), "--identify", "--frames=0", self.filename],
            stdout=subprocess.PIPE)
        while p.returncode is None:
            (out, err) = p.communicate()

        video_height_m = re.search("ID_VIDEO_HEIGHT=(\d*)", out)
        video_width_m = re.search("ID_VIDEO_WIDTH=(\d*)", out)
        self.height = float(video_height_m.groups()[0])
        self.width = float(video_width_m.groups()[0])

        seekable = re.search("ID_SEEKABLE=(\d*)", out)
        self.seekable = True if seekable.groups()[0] == '1' else False

        self.length = float(re.search("ID_LENGTH=([\d\.]*)", out).groups()[0])

    def start(self, *args):
        cmd = "{} --really-quiet".format(configure.get('MPLAYER')).strip().split()
        cmd += args
        cmd.append(self.filename)
        logger.debug('Running: %s', cmd)
        p = subprocess.Popen(cmd)
        p.wait()

class SlavePlayer(widget.OnFinished, widget.LoopAware):
    SEEK_RELATIVE = 0
    SEEK_PERCENTAGE = 1
    SEEK_ABSOLUTE = 2
    DEFAULT_CMD =('{player} --slave --quiet '
                  '--input=nodefault-bindings --noconfig=all '
                  '{extra} --geometry=1440x680+0+900')

    def __init__(self, filename, cmd=None, extra='', *args, **kwds):
        """loop is an optional eventloop.  If specified, the Player will yield to the
        event loop"""
        super(SlavePlayer, self).__init__(*args, **kwds)
        if not cmd:
            cmd = self.DEFAULT_CMD
        self.cmd = cmd.format(player=configure.get('MPLAYER'), extra=extra).split() + [filename]
        self.p = None
        self._paused = True

    def checkIfFinished(self, *args):
        if self.p.poll() is not None:
            self.onFinished()
        else:
            logger.debug('still playing')
            if self._loop:
                self._loop.set_alarm_in(1, self.checkIfFinished)

    def start(self):
        if not self.p:
            logger.debug('Running: %s', self.cmd)
            self.p = async_subprocess.AsyncPopen(
                self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self._paused = False
            self.checkIfFinished()

    def isPaused(self):
        return self._paused

    def communicate(self, cmd):
        # this needs to go into an alarm on the event loop
        # that is constantly parsing the output
        # and pulling things from a queue
        #
        # This way I can parse the EOF from mplayer
        # and know when to load up the next file
        #
        # it also enables other possible status to come in
        # through stdin
        return self.p.communicate(cmd + '\n')

    def getProperty(self, prop, parser, callback=None):
        def _callback(*args):
            if self.p.poll() is None:
                (out, err) = self.communicate(prop)
                t = parser(out)
                if t is not None:
                    if callback:
                        callback(t)
                    else:
                        return t
                elif callback and self._loop:
                    self._loop.set_alarm_in(0.02, _callback)
                else:
                    time.sleep(0.02)
                    return _callback()
        return _callback()

    def getTime(self, callback=None):
        return self.getProperty('get_time_pos', parseTime, callback=callback)

    def seekAndPlay(self, start, duration=None, end=None):
        if not duration and not end:
            raise Exception("duration or end must be specified")
        self.seek(start)
        if not end:
            end = start + duration
        logger.debug('Playing from %s to %s', start, end)
        self.play()
        def _callback(t):
            if t >= end:
                self.pause()
                logger.debug('Finished playing')
            else:
                self.getTime(_callback)
        self.getTime(_callback)

    def togglePause(self):
        self.communicate('pause')
        self._paused = not self._paused
        logger.debug('Paused: %s', self._paused)

    def play(self):
        if self._paused:
            self.togglePause()

    def pause(self):
        if not self._paused:
            self.togglePause()

    def seek(self, value, type_=SEEK_ABSOLUTE):
        self.communicate('seek {} {}'.format(value, type_))

    def quit(self):
        self.communicate('quit')

    def osd(self):
        self.communicate('osd')

    def changeVolume(self, step=1):
        self.communicate('volume {}'.format(step))
