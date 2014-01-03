import hashlib
import logging
import os.path
import platform
import sys

logger = logging.getLogger(__name__)

hostname = platform.node()

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

def configureLogging(level=logging.INFO, handlers=None):
    if not handlers:
        handlers = [standardConsoleHandler()]
    for handler in handlers:
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(level)
