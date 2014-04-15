import argparse
import os.path


parser = argparse.ArgumentParser()
parser.add_argument('playlist')
parser.add_argument('output')
args = parser.parse_args()

concat = 'concat_file'

a = range(5, 12)
b = range(5, 12)
random.shuffle(b)
mapping = {aa:bb for aa, bb in zip(a, b)}

with open(concat, 'w') as inpt:
    if args.playlist:
        with open(args.playlist) as f:
            for l in f:
                inpt.write("file '{}'\n".format(l.strip()))

subprocess.call(['ffmpeg', '-f', 'concat', '-i', concat, '-c', 'copy', args.output])
os.remove(concat)
