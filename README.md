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

### Fifth

Try it out!

run `python scripts/show_porn.py <path to a video>`


Notes
----------------------------

mplayer is run in slave mode, with the terminal reading in key commands and passing those along to mplayer.
This was a pretty cheap way to be able to control a video player, leaving time to work on the rest of the library.

It is a bit weird, but I've found that if I position my terminal in the bottom of the screen and set the GEOMETRY value in 
~/.porntool/config.py to use the rest of the screen that it works pretty well.  The biggest downside is that after starting a video
you have to alt-tab back to the terminal to put it into focus to recieve the key commands.