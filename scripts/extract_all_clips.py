import argparse
import logging
import os.path

from porntool import db
from porntool import extract
from porntool import script
from porntool import tables


parser = argparse.ArgumentParser(description='Extract all clips from porn collection')
parser.add_argument('output_dir', help='directory for output', default='.')
ARGS = parser.parse_args()

try:
    script.standardSetup(copy_db=False, file_handler=False)
    logging.info('****** Starting new script ********')

    all_clips = db.getSession().query(tables.Clip).filter(
        tables.Clip.active == 1)

    for clip in all_clips:
        output = os.path.join(ARGS.output_dir, '{:06d}.mp4'.format(clip.id_))
        if os.path.exists(output):
            continue
        try:
            extract.extractClip(clip, output)
        except KeyboardInterrupt:
            raise
        except:
            logging.exception('A bad thing happened on %s', clip.id_)
            continue
finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
