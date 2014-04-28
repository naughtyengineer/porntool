import collections
import codecs
import logging
import os
import subprocess

from porntool import player

logger = logging.getLogger(__name__)

Resolution = collections.namedtuple('Resolution', ('width', 'height'))
VIDEO = ['-vcodec', 'libx264', '-crf', '23', '-preset', 'medium', '-r', '30000/1001']
AUDIO = ['-acodec', 'aac', '-strict', 'experimental', '-ac', '2', '-ar', '44100', '-ab', '128k']

DEVNULL = open(os.devnull, 'w')


def resizeScale(input_resolution, output_resolution):
    height_scale = output_resolution.height / input_resolution.height
    width_scale = output_resolution.width / input_resolution.width
    if height_scale < width_scale:
        return height_scale
    else:
        return width_scale


def padAndScaleFilter(input_resolution, output_resolution):
    scale = resizeScale(input_resolution, output_resolution)
    new_height = input_resolution.height * scale
    new_width = input_resolution.width * scale
    y_diff = output_resolution.height - new_height
    x_diff = output_resolution.width - new_width
    # https://ffmpeg.org/ffmpeg-filters.html#scale
    scale_filter = 'scale=w={}:h={}'.format(new_width, new_height)
    # https://ffmpeg.org/ffmpeg-filters.html#pad
    pad_filter = 'pad=w={}:h={}:x={}:y={}:color=black'.format(
        output_resolution.width, output_resolution.height,
        x_diff / 2, y_diff / 2)
    return '{},{}'.format(scale_filter, pad_filter)


def extractClip(
        clip, output, target_resolution=None, clip_resolution=None,
        cleanup=True, reencode=False):
    input_ = clip.moviefile.getActivePath().path
    # seeking before input uses keyframes
    preseek = max(clip.start - 10, 0)
    # and then normal decoding after that
    postseek = clip.start - preseek
    # decided that mpegts wasn't the way to go
    # '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts',
    cmd = ['ffmpeg', '-y', '-ss', str(preseek), '-i', input_,
           '-ss', str(postseek), '-t', str(clip.duration)]

    if clip_resolution and target_resolution:
        cmd += ['-vf', padAndScaleFilter(clip_resolution, target_resolution)]

    if reencode:
        cmd = cmd + VIDEO + AUDIO
    else:
        cmd = cmd + ['-codec', 'copy']

    cmd += [output]
    logger.info('Extraction command: %s', cmd)
    def delete():
        logger.error("Failed to process {}".format(output))
        try:
            os.remove(output)
        except OSError:
            pass

    try:
        log_output = '{}.log'.format(clip.id_)
        with codecs.open(log_output, 'w', 'utf-8') as f:
            f.write(u'ffmpeg-{}\n'.format(' '.join(cmd)))
            if clip_resolution:
                f.write('Input Resolution: height: {}, width: {}\n'.format(
                    clip_resolution.height, clip_resolution.width))
            f.flush()
            returncode = subprocess.call(cmd, stderr=f)
    except:
        delete()
        raise
    if returncode != 0:
        delete()
        return False
    if cleanup:
        os.remove(log_output)
    return True


def testExtraction(output):
    try:
        util.identify(output)
        return True
    except:
        logger.error("ffmpeg created bad output for: {}".format(output))
        os.remove(output)
        return False


def getTargetResolutionClips(clips):
    unique_clips = {}
    for c in clips:
        if c.file_id not in unique_clips:
            unique_clips[c.file_id] = c
    filepaths = [c.moviefile.getActivePath() for c in unique_clips.values()]
    resolutions = [player.MoviePlayer(fp) for fp in filepaths]
    for mp in resolutions:
        mp.identify()
    return getTargetResolution(resolutions)


def getTargetResolution(resolutions):
    max_height = max([r.height for r in resolutions])
    max_width = max([r.width for r in resolutions])
    min_height = min([r.height for r in resolutions])
    min_width = min([r.width for r in resolutions])
    print "Common Resolutions:"
    print "16x9: 640x360, 854x480, 960x540, 1024x576, 1280x720"
    print "4x3:  320x240, 640x480, 800x600, 1024x768"
    print "Max Width:", max_width
    print "Max Height:", max_height
    print "Min Width:", min_width
    print "Min Height:", min_height
    r = raw_input("Enter Target Resolution: ")
    w,h = r.split('x')
    return Resolution(float(w), float(h))
