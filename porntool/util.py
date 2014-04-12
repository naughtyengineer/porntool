import hashlib
import logging
import os.path
import platform
import os
import subprocess
import sys

from porntool import configure
from porntool import db

logger = logging.getLogger(__name__)

hostname = platform.node()
_dot = hostname.find('.')
if _dot > 0:
    hostname = hostname[:_dot]

DEVNULL = open(os.devnull, 'w')

def flexibleBoolean(x):
    x = x.lower()
    if x in ('t', 'true', 'y', 'yes'):
        return True
    elif x in ('f', 'false', 'n', 'no'):
        return False
    raise pt.PorntoolException('Invalid boolean argument')


def hash_file(file_, sample_size, enable_warn=True):
    logger.info("Hashing %s", file_)
    sample_points = 4
    file_size = os.path.getsize(file_)
    if enable_warn and file_size < (sample_size * 4):
        logger.warn('Hashing %s despite being a small file')
    h = hashlib.sha1()
    f = open(file_)
    size = min(file_size / sample_points, sample_size)
    for i in range(0,sample_points):
        seek = i * file_size / sample_points
        f.seek(seek)
        h.update(f.read(size))
    hash = h.hexdigest()
    return hash


def standardConsoleHandler():
    result = logging.StreamHandler(sys.stdout)
    format_ = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    formatter = logging.Formatter(format_)
    result.setFormatter(formatter)
    return result


def standardFileHandler(filename):
    result = logging.FileHandler(filename)
    format_ = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    formatter = logging.Formatter(format_)
    result.setFormatter(formatter)
    return result


def configureLogging(level=logging.DEBUG, file_handler=True):
    if file_handler:
        logging.getLogger().addHandler(standardFileHandler('log'))
    else:
        logging.getLogger().addHandler(standardConsoleHandler())
    logging.getLogger().setLevel(level)
    logging.getLogger('urwid').setLevel('WARNING')


def identify(filename):
    logger.debug('Calling `identify` on %s', filename)
    p = subprocess.Popen(
        [configure.get('MPLAYER'), "--vo=null", "--ao=null", "--identify",
         "--frames=0", filename],
        stdout=subprocess.PIPE, stderr=DEVNULL)
    (out, err) = p.communicate()
    out = out.decode('utf-8')
    return out
