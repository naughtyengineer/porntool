import argparse
import json
import itertools
import os
import re

from porntool import db
from porntool import script
from porntool import tables

def parseClipFilename(clipfile):
    m = re.match('(\d{6,6}).mp4', clipfile)
    if m:
        return int(m.group(1))
    else:
        return None

def exportObject(instance, instance_type):
    d = {key: getattr(instance, key) for key in instance.__mapper__.c.keys()}
    d['obj_type'] = instance_type
    return d

parser = argparse.ArgumentParser()
parser.add_argument('input', help='newline delimited json')
args = parser.parse_args()

try:
    script.standardSetup(copy_db=False)
    session = db.getSession()

    tags = {}
    girls = {}
    movies = {}
    clips = {}

    with open(args.input) as fin:
        for line in fin:
            d = json.loads(line.strip())
            # allow the database to assign the ID
            # so pop it off
            # but we still need it for internal references
            id_ = d.pop('id_')
            obj_type = d.pop('obj_type')

            if obj_type == 'tag':
                t = tables.Tag(**d)
                tags[id_] = t

            elif obj_type == 'girl':
                g = tables.Girl(**d)
                girls[id_] = g

            elif obj_type == 'movie':
                girl_ids = d.pop('girls')
                tag_ids = d.pop('tags')
                m = tables.MovieFile(**d)
                m.girls = [girls[i] for i in girl_ids]
                m.tags = [tags[i] for i in tag_ids]
                movies[id_] = m

            elif obj_type == 'clip':
                tag_ids = d.pop('tags')
                c = tables.Clip(**d)
                c.tags = [tags[i] for i in tag_ids]
                clips[id_] = c
            else:
                raise Exception('Invalid Object type: %s' % obj_type)
    session.add_all(tags.values())
    session.add_all(girls.values())
    session.add_all(movies.values())
    session.flush()

    for clip in clips.values():
        # have to switch the file_id to the
        # new one for the file
        clip.file_id = movies[clip.file_id].id_

    session.add_all(clips.values())
    session.commit()
finally:
    script.standardCleanup()
