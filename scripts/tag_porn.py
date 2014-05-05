import argparse

from porntool import db
from porntool import movie
from porntool import script
from porntool import tag

parser = argparse.ArgumentParser(description='Play your porn collection')
parser.add_argument('files', nargs='+', help='files to play')
parser.add_argument('--tags', nargs='+', help='tags to add to each file')
args = parser.parse_args()

if not args.tags:
    raise Exception("Must specify at least one tag")

script.standardSetup(file_handler=False, copy_db=False)

try:
    tags = [tag.getTag(t) for t in args.tags]
    filepaths = movie.loadFiles(args.files, add_movie=movie.addMovie)
    for fp in filepaths:
        for tag_ in tags:
            if tag_ not in fp.pornfile.tags:
                fp.pornfile.tags.append(tag_)
finally:
    db.getSession().commit()
    script.standardCleanup()
