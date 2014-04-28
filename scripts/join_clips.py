import argparse
import os
import subprocess

from porntool import configure

configure.load()

parser = argparse.ArgumentParser()
parser.add_argument('playlist')
parser.add_argument('output')
args = parser.parse_args()

concat = 'concat_file'

with open(concat, 'w') as inpt:
    if args.playlist:
        with open(args.playlist) as f:
            for l in f:
                inpt.write("file '{}'\n".format(l.strip()))

video = configure.get('VIDEO')
audio = configure.get('AUDIO')

subprocess.call(['ffmpeg', '-f', 'concat', '-i', concat, '-c', 'copy', args.output])
os.remove(concat)
