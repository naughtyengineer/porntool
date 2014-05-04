import argparse
import collections
import datetime
import itertools
import logging
import random
import os.path
import subprocess

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

Color = collections.namedtuple('Color', ['hex_code', 'name'])
BLACK = Color('000000', 'black')
WHITE = Color('ffffff', 'white')

def ensureProperties(inventory):
    for fp in inventory:
        movie.updateMissingProperties(fp)
        yield fp


def choseFilenames(image_filenames, solid_filenames, count):
    all_filenames = image_filenames[:count]
    if len(image_filenames) > count:
        return all_filenames

    n_solid = count - len(image_filenames)
    picked_solids = [random.choice(solid_filenames) for _ in range(n_solid)]
    logging.debug('n_solid: %s, len(picked_solids): %s', n_solid, len(picked_solids))
    for p in picked_solids:
        all_filenames.insert(random.randint(0, len(all_filenames)), p)
    logging.debug('Using %s images', len(all_filenames))
    return all_filenames


def saveClips(clips, filename, image_filenames, solid_filenames):
    f = open(filename, 'w')
    clip_filenames = ['{:05d}.mp4'.format(c.id_) for c in clips]
    image_clips = choseFilenames(image_filenames, solid_filenames, len(clips) - 1)
    all_filenames = []
    for clip, image in itertools.izip_longest(clip_filenames, image_clips):
        all_filenames.append(clip)
        if image:
            all_filenames.append(image)
        else:
            logging.debug('Image is None')
    f.writelines('\n'.join(all_filenames))


def makeSolidClips(output_dir, color, resolution, frame_lengths):
    # first, use image magik to make a solid color
    image_file_name = os.path.join(output_dir, '{}.png'.format(color.name))
    subprocess.call('convert -size {}x{} xc:#{} {}'.format(
        resolution.width, resolution.height, color.hex_code, image_file_name).split())
    file_names = []
    for length in frame_lengths:
        movie_file_name = '{}-{:03d}.mp4'.format(color.name, length)
        file_names.append(movie_file_name)
        movie_file_path = os.path.join(output_dir, movie_file_name)
        if os.path.exists(movie_file_path):
            continue
        cmd = ('ffmpeg -loop 1 -i'.split() +
               [image_file_name] +
               '-c:v libx264 -frames {} -r 30000/1001 -pix_fmt yuv420p'.format(length).split() +
               [movie_file_path])
        print cmd
        subprocess.call(cmd)
    return file_names


def clipFromImage(output_dir, image_filename, resolution, frames):
    basename = os.path.basename(image_filename)
    tmp_filename = '/tmp/{}'.format(basename)
    file_root, file_ext = os.path.splitext(basename)
    another_name = file_root + ".mp4"
    output_movie = os.path.join(output_dir, another_name)
    convert_cmd = ['convert', image_filename, '-resize',
                   '{}x{}^'.format(resolution.width, resolution.height), tmp_filename]
    print convert_cmd
    subprocess.call(convert_cmd)
    cmd = ('ffmpeg -loop 1 -i'.split() +
           [tmp_filename] +
           '-c:v libx264 -frames {} -r 30000/1001 -pix_fmt yuv420p'.format(frames).split() +
           [output_movie])
    print cmd
    subprocess.call(cmd)
    return another_name

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
parser.add_argument('--images', nargs='*', help='images to insert between clips')
ARGS = parser.parse_args()

try:
    script.standardSetup(copy_db=False, file_handler=False)
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

    playlist = os.path.join(ARGS.output, 'playlist-{}.txt'.format(
        datetime.datetime.now().strftime('%Y%m%d%H%M')))
    whites = makeSolidClips(ARGS.output, WHITE, resolution, [3, 3, 3,  4,  4,  5,  6,  7,  8])
    blacks = makeSolidClips(ARGS.output, BLACK, resolution, [9, 9, 9, 10, 10, 11, 12, 13, 14])
    logging.debug('len(whites) = %s', len(whites))
    logging.debug('len(blacks) = %s', len(blacks))
    image_clip_filenames = []
    if ARGS.images:
        for image in ARGS.images[:len(clips)]:
            image_clip = clipFromImage(ARGS.output, image, resolution, random.randint(3, 15))
            image_clip_filenames.append(image_clip)

    extracted_clips = processClips(clips, ARGS.output, ARGS.quick, resolution)
    saveClips(extracted_clips, playlist, image_clip_filenames, whites+blacks)

finally:
    script.standardCleanup()
    logging.info('****** End of Script *********')
