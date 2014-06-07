import collections
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

def extractClip(clip, output, target_resolution, clip_resolution, cleanup=True):
    input_ = clip.moviefile.getActivePath().path
    # seeking before input uses keyframes
    preseek = max(clip.start - 10, 0)
    # and then normal decoding after that
    postseek = clip.start - preseek
    # decided that mpegts wasn't the way to go
    # '-bsf:v', 'h264_mp4toannexb', '-f', 'mpegts',
    cmd = (['ffmpeg', '-y', '-ss', str(preseek), '-i', input_, '-ss', str(postseek),
           '-t', str(clip.duration),
            '-vf', padAndScaleFilter(clip_resolution, target_resolution)] +
           VIDEO + AUDIO + [output])
    logger.info('Extraction command: %s', cmd)
    def delete():
        logger.error("Failed to process {}".format(output))
        try:
            os.remove(output)
        except OSError:
            pass

    try:
        log_output = '{}.log'.format(clip.id_)
        with open(log_output, 'w') as f:
            f.write('ffmpeg-{}\n'.format(' '.join(cmd)))
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
