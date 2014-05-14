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
parser.add_argument('clip_dir')
parser.add_argument('-o', default='export.json')
args = parser.parse_args()

try:
    script.standardSetup(copy_db=False)

    session = db.getSession()

    clips = {c.id_: c for c in session.query(tables.Clip)}

    parsed_ids = [parseClipFilename(clipfile) for clipfile in os.listdir(args.clip_dir)]
    extracted_ids = set(c for c in parsed_ids if c)
    extracted_clips = {key: clips[key] for key in extracted_ids}
    extracted_files = {c.moviefile.id_: c.moviefile for c in extracted_clips.itervalues()}
    extracted_girls = {g.id_: g for g in itertools.chain.from_iterable(
            f.girls for f in extracted_files.itervalues())}
    extracted_tags = {t.id_: t for t in itertools.chain.from_iterable(
            f.tags for f in extracted_files.itervalues())}
    extracted_tags.update({t.id_: t for t in itertools.chain.from_iterable(
                c.tags for c in extracted_clips.itervalues())})

    to_export = []

    for tag in extracted_tags.values():
        to_export.append(exportObject(tag, 'tag'))

    for girl in extracted_girls.values():
        to_export.append(exportObject(girl, 'girl'))

    for f in extracted_files.values():
        d = exportObject(f, 'movie')
        del d['last']
        d['tags'] = [t.id_ for t in f.tags]
        d['girls'] = [g.id_ for g in f.girls]
        to_export.append(d)

    for clip in extracted_clips.values():
        d = exportObject(clip, 'clip')
        d['tags'] = [t.id_ for t in clip.tags]
        to_export.append(d)

    with open(args.o, 'w') as fout:
        for o in to_export:
            json.dump(o, fout)
            fout.write('\n')

finally:
    script.standardCleanup()
