# The full path to the mplayer executable.
# mplayer2 is also acceptable
MPLAYER='/usr/bin/mplayer'

# The GEOMETRY value is passed directly
# to MPLAYER and determings the starting position
GEOMETRY='--geometry=1920x1080+320+0'

# The desired location of the database
SQL_FILE='~/.porntool/porntool.db'

########################
# ffmpeg configuration
#
# VIDEO: set the VIDEO variable to what codec and settings should be
#        used for encoding video streams
#
# AUDIO: set the AUDIO variable to what codec and settings should be
#        used for encoding audio streams

# use x264 to encode, https://trac.ffmpeg.org/wiki/x264EncodingGuide
# -crf is the constant quality, 23 is the default.  lower is better, 18-28 is considered sane
# -preset is a tradeoff between encoding speed/file size. Slower -> smaller file
# the framerate (-r) is necessary when joining clips
VIDEO = ['-vcodec', 'libx264', '-crf', '23', '-preset', 'medium', '-r', '30000/1001']


# http://trac.ffmpeg.org/wiki/Encoding%20VBR%20(Variable%20Bit%20Rate)%20mp3%20audio
AUDIO = '-codec:a libmp3lame -qscale:a 3'.split()

# This one might be better
# http://trac.ffmpeg.org/wiki/AACEncodingGuide
# AUDIO = '-codec:a libfdk_aac -profile:a aac_he_v2 -b:a 32k'.split()

# and this one disables the audio
# AUDIO = ['-an']
