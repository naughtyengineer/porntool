import datetime as dt
import logging

import porntool as pt
from porntool import tables

logger = logging.getLogger(__name__)

_session = None

def setSession(session):
    global _session
    logger.info('Setting the session')
    if _session:
        logger.warn('_session is already set')
    _session = session

def getSession():
    if not _session:
        raise pt.PorntoolException('No session set')
    return _session

def saveUsage(movie, length, timestamp=None):
    timestamp = timestamp or dt.datetime.now()
    u = tables.Usage.insert().values(
        file_id=movie.id_, timestamp=timestamp, time_=length)
    getSession().execute(u)
