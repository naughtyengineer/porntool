import subprocess

from porntool import configure

class MoviePlayer(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def play(self):
        cmd = "{} -fs".format(configure.get('MPLAYER')).strip().split()
        cmd.append(self.filepath.path)
        print cmd
        with open('mplayer.log', 'w') as f:
            p = subprocess.Popen(cmd)
            p.wait()
