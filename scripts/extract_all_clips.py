import argparse
import logging
import os.path

from porntool import db
from porntool import extract
from porntool import filters
from porntool import movie
from porntool import player
from porntool import script


parser = argparse.ArgumentParser(
    description='Extract all clips from porn collection', parents=[filters.PARSER])
parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
parser.add_argument('--output-dir', help='directory for output', default='.')
parser.add_argument('--project-id', type=int, default=0)
parser.add_argument('--resolution', help="if not specified, use movie's original resolution")
ARGS = parser.parse_args()

try:
    if ARGS.resolution:
        w,h = ARGS.resolution.split('x')
        resolution = extract.Resolution(float(w), float(h))
    else:
        resolution = None

    script.standardSetup(copy_db=False, file_handler=False)
    logging.info('****** Starting new script ********')

    cmd_line_files = [f.decode('utf-8') for f in ARGS.files]
    filepaths = movie.queryFiles(cmd_line_files)
    logging.debug('filepaths: %s', len(filepaths))
    db.getSession().commit()
    logging.debug('%s files loaded', len(filepaths))

    all_filters = filters.applyArgs(ARGS, db.getSession())

    all_clips = []
    for filepath in movie.MovieInventory(filepaths, False, all_filters):
        for clip in filepath.pornfile._clips:
            if clip.active and clip.project_id == ARGS.project_id:
                all_clips.append(clip)

    for clip in all_clips:
        output = os.path.join(ARGS.output_dir, '{:06d}.mp4'.format(clip.id_))
        if os.path.exists(output):
            continue
        try:
            if resolution:
                mp = player.identify(clip.moviefile.getActivePath())
                extract.extractClip(clip, output, resolution, mp)
            else:
                extract.extractClip(clip, output)
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('A bad thing happened on %s', clip.id_)
            continue
finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
