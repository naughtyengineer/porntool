import argparse

from porntool import db
from porntool import movie
from porntool import script


parser = argparse.ArgumentParser()
parser.add_argument('directory')
args = parser.parse_args()

try:
    script.standardSetup(copy_db=False, file_handler=False)
    movie.loadFiles(args.directory, movie.addMovie)
    db.getSession().commit()
finally:
    script.standardCleanup()
