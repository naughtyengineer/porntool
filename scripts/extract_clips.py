import argparse
import datetime
import logging
import os.path

from porntool import clippicker
from porntool import db
from porntool import extract
from porntool import filters
from porntool import movie
from porntool import player
from porntool import rating
from porntool import script
from porntool import segment
from porntool import tables as t
from porntool import util

def ensureProperties(inventory):
    for fp in inventory:
        movie.updateMissingProperties(fp)
        yield fp


def saveClips(clips, filename):
    f = open(filename, 'w')
    f.writelines(['{:05d}.mp4\n'.format(c.id_) for c in clips])


def processClips(clips, output_dir, quick=False, resolution=None):
    duration = 0
    start = datetime.datetime.now()
    success = []
    for i, clip in enumerate(clips):
        output = os.path.join(output_dir, '{:05d}.mp4'.format(clip.id_))
        if os.path.exists(output):
            success.append(clip)
            continue
        fp = clip.moviefile.getActivePath()
        if not fp:
            print "Missing file for Clip", clip.id_
            continue
        input_ = fp.path
        mp = player.identify(fp) if not quick else None
        if not extract.extractClip(clip, output, resolution, mp, cleanup=False, reencode=True):
            continue
        #if not extract.testExtraction(output):
        #    continue
        duration += clip.duration
        print "Done with {} from Clip {} for {} seconds total ({})".format(
            i, clip.id_, duration, datetime.datetime.now() - start)
        success.append(clip)
    return success

segment_trackers = {
    'new': segment.PriorityRandomSegmentTracker,
    'existing': segment.ExistingSegmentTracker,
    'sample': lambda fp, n: segment.CountSegmentTracker(fp, n, 10),
}

clip_types = {
    'least': clippicker.ClipPicker,
    'shuffle': clippicker.RandomClipPicker,
    'new': clippicker.OnlyNewClips,
}

parser = argparse.ArgumentParser(description='Extract clips from porn collection')
parser.add_argument('files', nargs='+', help='files to play; play entire collection if omitted')
parser.add_argument('--output', help='directory for output', default='.')
parser.add_argument('--time', default=10, type=int, help="minutes of clips to extract")
parser.add_argument('--shuffle', default=True, type=util.flexibleBoolean)
parser.add_argument(
    '-n', '--nfiles', default=20, type=int, help='number of files to rotate through')
parser.add_argument('--clip-type', choices=clip_types.keys(), default='shuffle')
parser.add_argument('--tracker', choices=segment_trackers.keys(), default='existing')
parser.add_argument('--extra', default='', help='extra args to pass to player')
parser.add_argument('--quick', action='store_true', help='set to not reencode, just extract')
parser.add_argument('--resolution')
ARGS = parser.parse_args()

try:
    script.standardSetup()
    logging.info('****** Starting new script ********')

    filepaths = []
    for file_ in ARGS.files:
        some_filepaths = db.getSession().query(t.FilePath).filter(
            (t.FilePath.hostname == util.hostname) &
            (t.FilePath.path.like('{}%'.format(file_)))
        ).all()
        filepaths.extend(some_filepaths)

    inventory = movie.MovieInventory(
        filepaths, ARGS.shuffle,
        [filters.Exists(), filters.ByMinCount(db.getSession(), 1),
         filters.ExcludeTags(['pmv', 'cock.hero'])])
    inventory = ensureProperties(inventory)

    normalratings = rating.NormalRatings(db.getSession())

    segment_tracker = segment_trackers[ARGS.tracker]
    clip_type = clip_types[ARGS.clip_type]
    clip_picker = clip_type(inventory, normalratings, ARGS.nfiles, segment_tracker)

    target_time = ARGS.time * 60
    actual_time = 0
    clips = []
    while actual_time < target_time:
        next_clip = clip_picker.getNextClip()
        if not next_clip:
            break
        actual_time += next_clip.duration
        clips.append(next_clip)

    if not ARGS.quick:
        if ARGS.resolution:
            w,h = ARGS.resolution.split('x')
            resolution = extract.Resolution(float(w), float(h))
        else:
            resolution = extract.getTargetResolutionClips(clips)
    else:
        resolution = None

    playlist = os.path.join(ARGS.output, 'playlist.txt')
    success = processClips(clips, ARGS.output, ARGS.quick, resolution)
    saveClips(success, playlist)

finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
