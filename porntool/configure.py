import os.path

CONFIGURATION = {}

def load(conf_file='~/.porntool/config.py'):
    global CONFIGURATION
    conf = {}
    exec(open(os.path.expanduser('~/.porntool/config.py')).read(), {}, conf)
    CONFIGURATION = conf
    print "SETTING", CONFIGURATION
    return conf

def get(key):
    print "getting", CONFIGURATION
    return CONFIGURATION.get(key)
