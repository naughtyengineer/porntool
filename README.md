porntool
========

This is a library and a set of scripts to help curate a collection of
porn videos and pictures.

It is designed to let you:
 * tag videos
 * track performers
 * rate videos
 * record usage
 * extract highlight clips

There also exists some basic functionality to automatically create a
compilation of clips, a hightlight reel, similar to a porn music
video.  This part is under active development.

Installation
---------------------

### First

install `mplayer` and `ffmpeg`. `mplayer` is used heavily for viewing videos and `ffmpeg` is 
used to extract clips and create compilations.

ffmpeg has a lot of different compilation options to setup different encoders.  

### Second

clone this repo and run:

`$ pip install .`

SQLAlchemy and urwid are dependencies and they should be automatically
installed if you don't already have them.

`numpy` and `scipy` are recommended, but not required.  They will
enable a better rating system.

### Third

Create a file `~/.porntool/config.py`. Look at `example-config.py`
for more information.

### Fourth

run `python setup_db.py` to create the necessary sqlite database.