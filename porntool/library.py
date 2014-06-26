import argparse

from porntool import movie

def getParser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('files', nargs='*', help='files to play; play entire collection if omitted')
    parser.add_argument('--update-library', action='store_true', default=False)
    return parser


def getFilePaths(ARGS):
    cmd_line_files = [f.decode('utf-8') for f in ARGS.files]
    if ARGS.update_library:
        filepaths = movie.loadFiles(cmd_line_files, add_movie=movie.addMovie)
    else:
        filepaths = movie.queryFiles(cmd_line_files)
    return filepaths
