import logging

import porntool as pt

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
