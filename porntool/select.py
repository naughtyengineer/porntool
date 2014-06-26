import argparse

from porntool import clippicker
from porntool import segment


def getParser(default_clip_type='shuffle', default_tracker='sample'):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '-n', '--nfiles', default=20, type=int, help='number of files to rotate through')
    parser.add_argument('--clip-type', choices=('least', 'shuffle'), default=default_clip_type)
    parser.add_argument('--tracker', choices=('new', 'existing', 'sample'), default=default_tracker)
    parser.add_argument('--sample-size', default=10, type=int)
    parser.add_argument('--max-clips', type=int, help=(
            'when selecting movies, only pick ones that have less then this many '
            'clips already reviewed'))
    return parser


def getClipPickerType(args, extras=None):
    extras = extras or []
    if args.clip_type == 'least':
        mixins = [clippicker.Least]
    elif args.clip_type == 'shuffle':
        mixins = [clippicker.Random]
    else:
        raise Exception()

    if args.max_clips:
        mixins.append(clippicker.OnlyNClips(args.max_clips))
    elif args.tracker == 'sample':
        mixins.append(clippicker.OnlyNClips(args.sample_size))

    for extra in extras:
        mixins.append(extra)

    # the base has to be last
    mixins.append(clippicker.ClipPicker)

    class _ClipPicker(clippicker.ClipPicker): pass
    _ClipPicker.__bases__ = tuple(mixins)
    return _ClipPicker


def getSegmentTrackerType(args):
    segment_trackers = {
        'new': segment.PriorityRandomSegmentTracker,
        'existing': segment.ExistingSegmentTracker,
        'sample': lambda fp, proj, rating: segment.CountSegmentTracker(
            fp, proj, rating, args.sample_size)
        }
    return segment_trackers[args.tracker]
