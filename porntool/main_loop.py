#The only purpose of this module is to access the global main loop

_LOOP = None

def set(loop):
    global _LOOP
    _LOOP = loop

def get():
    return _LOOP
