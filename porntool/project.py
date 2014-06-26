import argparse

from sqlalchemy import orm

from porntool import db
from porntool import tables

def getProject(args):
    name = args.project
    try:
        PROJECT = db.getSession().query(tables.Project).filter(tables.Project.name==name).one()
    except orm.exc.NoResultFound:
        PROJECT = t.Project(name=name)
        db.getSession().add(PROJECT)
    return PROJECT


def getParser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--project', default='base')
    return parser
