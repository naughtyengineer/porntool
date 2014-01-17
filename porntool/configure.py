import logging
import os.path

logger = logging.getLogger(__name__)

CONFIGURATION = {}

def load(conf_file='~/.porntool/config.py'):
    conf = {}
    exec(open(os.path.expanduser(conf_file)).read(), {}, conf)
    CONFIGURATION.update(conf)
    return conf

def get(key):
    return CONFIGURATION.get(key)
