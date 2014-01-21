from porntool import db
from porntool import tables

_cache = {}

def getTag(tag):
    _loadAllTags()
    tag_object = _cache.get(tag)
    if not tag_object:
        tag_object = tables.Tag(tag=tag)
        _cache[tag] = tag_object
        db.getSession().add(tag_object)
    return tag_object

def _loadAllTags():
    if not _cache:
        tags = db.getSession().query(tables.Tag)
        for tag in tags:
            _cache[tag.tag] = tag
