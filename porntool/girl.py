from porntool import db
from porntool import tables

_cache = {}

def getGirl(name):
    _loadAllTags()
    girl_object = _cache.get(name)
    if not girl_object:
        girl_object = tables.Girl(name=name)
        _cache[name] = girl_object
        db.getSession().add(girl_object)
    return girl_object

def _loadAllTags():
    if not _cache:
        girls = db.getSession().query(tables.Girl)
        for girl in girls:
            _cache[girl.name] = girl
