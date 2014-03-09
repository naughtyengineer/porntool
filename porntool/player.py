import collections as cols
import logging
import os
import re
import subprocess
import time

from porntool import async_subprocess
from porntool import configure
from porntool import db
from porntool import tables
from porntool import widget

logger = logging.getLogger(__name__)
TRACE = logging.DEBUG - 1
DEVNULL = open(os.devnull, 'w')

class MoviePlayer(object):
    def __init__(self, filename):
        self.filename = filename

    def identify(self):
        logger.debug('Calling `identify` on %s', self.filename)
        p = subprocess.Popen(
            [configure.get('MPLAYER'), "--vo=null", "--ao=null", "--identify",
             "--frames=0", self.filename],
            stdout=subprocess.PIPE, stderr=DEVNULL)
        (out, err) = p.communicate()

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



    def start(self, *args):
        cmd = "{} --really-quiet".format(configure.get('MPLAYER')).strip().split()
        cmd += args
        cmd.append(self.filename)
        logger.debug('Running: %s', cmd)
        p = subprocess.Popen(cmd)
        p.wait()

class OutputParser(object):
    stdin = ''
    def __init__(self, on_success):
        self.active = True
        self._on_success = [on_success]

    def __call__(self, output):
        pass

    def onSuccess(self, *args):
        for f in self._on_success:
            if f:
                f(*args)

class IsFinishedParser(OutputParser):
    def __call__(self, output):
        m = re.search('Exiting', output)
        if m:
            self.onSuccess()
        self.active = False

class TimePosParser(OutputParser):
    stdin = 'get_time_pos\n'
    def __call__(self, output):
        if output:
            m = re.match('ANS_TIME_POSITION=([\d\.]+)', output)
            if m:
                self.onSuccess(float(m.group(1)))


class SlavePlayer(widget.OnFinished, widget.LoopAware):
    SEEK_RELATIVE = 0
    SEEK_PERCENTAGE = 1
    SEEK_ABSOLUTE = 2
    DEFAULT_CMD =('{player} --slave --quiet '
                  '--input=nodefault-bindings --noconfig=all '
                  '{extra} --geometry=1440x640+0+900')
    # --msglevel=global=6
    # has a line like: EOF code: XXX

    def __init__(self, filepath, cmd=None, extra=''):
        filename = filepath.path
        self.filepath = filepath
        if not cmd:
            cmd = self.DEFAULT_CMD
        self.cmd = cmd.format(player=configure.get('MPLAYER'), extra=extra).split() + [filename]
        self.p = None
        self.playtime = 0
        self._log = open('mplayer.log', 'w')
        self._paused = True
        self._finished = False
        self._starttime = None
        self._current_position = None
        self._input = []
        self._parsers = [IsFinishedParser(self.onFinished), TimePosParser(self._setPos)]
        self._scrub_start = 0
        self.save_scrub = True
        widget.OnFinished.__init__(self)
        widget.LoopAware.__init__(self)

    def saveScrub(self, end):
        # should probably just make this available and have the caller save it
        if self.save_scrub and self._scrub_start is not None:
            db.getSession().execute(tables.Scrub.insert().values(
                file_id=self.filepath.file_id, start=self._scrub_start, end=end))
            self._scrub_start = None

    def _setPos(self, pos):
        self._current_position = pos

    def onFinished(self, **kwds):
        logger.info('SlavePlayer.onFinished called')
        self.saveScrub(self.getTime())
        self._finished = True
        self.updatePlaytime()
        if self.p.poll() is None:
            logger.error('The mplayer process is still running')
            self.p.terminate()
            self.p.wait()
        else:
            logger.info('mplayer has successfully finished')
            del self.p
        super(SlavePlayer, self).onFinished(**kwds)

    def updatePlaytime(self):
        if self._starttime:
            self.playtime += time.time() - self._starttime
            self._starttime = None
            logger.debug('Movie played for %s seconds', self.playtime)
        else:
            self._starttime = time.time()

    # def checkIfFinished(self, *args):
    #     if self.p.poll() is not None:
    #         self.updatePlaytime()
    #         self.onFinished()
    #     else:
    #         logger.log(TRACE, 'still playing')
    #         if self._loop:
    #             self._loop.set_alarm_in(1, self.checkIfFinished)

    def start(self):
        if not self.p:
            logger.debug('Running: %s', self.cmd)
            self.p = async_subprocess.AsyncPopen(
                self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self.communicate('osd 0') #turn off the osd
            self.updatePlaytime()
            self._paused = False
            self._run()

    def __del__(self):
        self._log.close()

    def _run(self):
        cmds = ''.join([parser.stdin for parser in self._parsers])
        out, err = self.p.communicate(cmds)
        if out:
            self._log.write(out)
            for parser in self._parsers:
                parser(out)
        if not self._finished:
            self._loop.alarm(.2, self._run)

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
        # through stdout
        logger.debug('command: %s', cmd)
        if hasattr(self, 'p'):
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
                    self._loop.alarm(0.02, _callback)
                else:
                    time.sleep(0.02)
                    return _callback()
        return _callback()

    def getTime(self):
        return self._current_position

    def seekAndPlay(self, start, duration=None, end=None, onFinished=None):
        if not duration and not end:
            raise Exception("duration or end must be specified")
        self.seek(start)
        if not end:
            end = start + duration
        logger.debug('Playing from %s to %s', start, end)
        self.play()
        def _callback():
            t = self.getTime()
            if self._finished:
                logger.debug('Finished playing')
                if onFinished:
                    onFinished()
            elif t >= end:
                self.pause()
                logger.debug('Reached the end of our clip')
                if onFinished:
                    onFinished()
            else:
                self._loop.alarm(0.1, _callback)
        # have to set a bigger value here to give mplayer enough
        # time to actually jump around in the file
        self._loop.alarm(0.5, _callback)

    def togglePause(self):
        self.updatePlaytime()
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
        now = self.getTime()
        self.saveScrub(now)
        if type_ == self.SEEK_ABSOLUTE:
            self._scrub_start = value
        elif type_ == self.SEEK_RELATIVE:
            self._scrub_start = now + value
        elif type_ == self.SEEK_PERCENTAGE:
            logger.warn('cannot calculate scrub start')
        self.communicate('seek {} {}'.format(value, type_))

    def quit(self):
        self.communicate('quit')

    def osd(self):
        self.communicate('osd')

    def changeVolume(self, step=1):
        self.communicate('volume {}'.format(step))
