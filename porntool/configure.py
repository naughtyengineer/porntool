import logging
import os.path

logger = logging.getLogger(__name__)

CONFIGURATION = {}

def load(conf_file='~/.porntool/config.py'):
    conf_file = os.path.expanduser(conf_file)
    logger.info('Loading configuration from %s', conf_file)
    conf = {}
    exec(open(conf_file).read(), {}, conf)
    for key in conf:
        value = conf[key]
        if isinstance(value, basestring):
            conf[key] = os.path.expanduser(os.path.expandvars(conf[key]))
    CONFIGURATION.update(conf)
    return conf

def get(key):
    return CONFIGURATION.get(key)
