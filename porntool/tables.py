import json
import os.path


import sqlalchemy as sql
from sqlalchemy.ext import declarative
from sqlalchemy import orm

Base =  declarative.declarative_base()


file_girl_association = sql.Table('file_girl', Base.metadata,
    sql.Column('girl_id', sql.Integer, sql.ForeignKey('girl.id')),
    sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id')))

file_tag_association = sql.Table('file_tag', Base.metadata,
    sql.Column('tag_id', sql.Integer, sql.ForeignKey('tag.id')),
    sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id')))

girl_tag_association = sql.Table('girl_tag', Base.metadata,
    sql.Column('tag_id', sql.Integer, sql.ForeignKey('tag.id')),
    sql.Column('girl_id', sql.Integer, sql.ForeignKey('girl.id')))

clip_tag_association = sql.Table('clip_tag', Base.metadata,
    sql.Column('tag_id', sql.Integer, sql.ForeignKey('tag.id')),
    sql.Column('clip_id', sql.Integer, sql.ForeignKey('clip.id')))


class PornFile(Base):
    __tablename__ = 'file'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    hash_ = sql.Column('hash', sql.String)
    # 0 means not active
    active = sql.Column(sql.Integer)
    size = sql.Column(sql.Integer)
    _type = sql.Column('type', sql.String)

    paths = orm.relationship('FilePath', backref=orm.backref('pornfile'))
    tags = orm.relationship(
        'Tag', secondary=file_tag_association, backref=orm.backref('pornfiles'))

    __mapper_args__ = {
        'polymorphic_identity': 'file',
        'polymorphic_on': _type
    }

    def getActivePath(self):
        for path in self.paths:
            if os.path.exists(path.path):
                return path

    def tagString(self):
        return " ".join([t.tag for t in self.tags if not t.tag.startswith('file:')])

    def girlString(self):
        return " ".join([g.name for g in self.girls])

class MovieFile(PornFile):
    __tablename__ = 'movie'
    id_ = sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id'), primary_key=True)
    last = sql.Column(sql.DateTime)
    length = sql.Column(sql.Float)

    girls = orm.relationship(
        'Girl', secondary=file_girl_association, backref=orm.backref('pornfiles'))

    __mapper_args__ = {
        'polymorphic_identity':'movie',
    }

    def getPlayCount(self, session):
        query = sql.select([sql.func.count('*')]).select_from(Usage).where(
            Usage.c.file_id == self.id_)
        playcount = session.execute(query).fetchone()[0]
        return playcount


class PictureFile(PornFile):
    __tablename__ = 'picture'
    id_ = sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id'), primary_key=True)
    rating = sql.Column(sql.Integer)

    __mapper_args__ = {
        'polymorphic_identity':'picture',
    }


# TODO: add support for aliases
class Girl(Base):
    __tablename__ = 'girl'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    name = sql.Column(sql.String)

    tags = orm.relationship(
       'Tag', secondary=girl_tag_association, backref=orm.backref('girls'))


class FilePath(Base):
    __tablename__ = 'file_path'
    file_id = sql.Column(sql.Integer, sql.ForeignKey('file.id'))
    hostname = sql.Column(sql.String, primary_key=True)
    path = sql.Column(sql.String, primary_key=True)

    def __repr__(self):
        return '{}({}, {})'.format(
            self.__class__.__name__, self.hostname, self.path.encode('utf-8'))

    def filename(self):
        return os.path.basename(self.path)


class Tag(Base):
    __tablename__ = 'tag'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    tag = sql.Column(sql.String)


class NormalRating(Base):
    __tablename__ = 'normalrating'
    file_id = sql.Column(sql.Integer, sql.ForeignKey('file.id'), primary_key=True)
    rating_adjustment = sql.Column(sql.Float)


class Project(Base):
    __tablename__ = 'project'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    name = sql.Column(sql.String)


class Clip(Base):
    """tag subsections of movies for highlights"""
    __tablename__ = 'clip'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    file_id = sql.Column(sql.Integer, sql.ForeignKey('movie.file_id'))
    project_id = sql.Column(sql.Integer, sql.ForeignKey('project.id'))
    start = sql.Column(sql.Float)
    duration = sql.Column(sql.Float)
    # 0 means not active
    active = sql.Column(sql.Integer)

    moviefile = orm.relationship('MovieFile', backref=orm.backref('_clips'))
    tags = orm.relationship(
        'Tag', secondary=clip_tag_association, backref=orm.backref('_clips'))

    @property
    def end(self):
        return self.start + self.duration

    def setStart(self, value, hold='end'):
        if hold == 'end':
            self.duration = self.end - value
        self.start = value

    def setEnd(self, value, hold='start'):
        if hold == 'start':
            self.duration = value - self.start
        else:
            self.start = value - self.duration


class Flag(Base):
    """flag a location in a movie - probably because its good"""
    __tablename__ = 'flag'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    file_id = sql.Column(sql.Integer, sql.ForeignKey('movie.file_id'))
    location = sql.Column(sql.Float)
    audio_only = sql.Column(sql.Boolean, default=False)
    moviefile = orm.relationship('MovieFile', backref=orm.backref('flags'))


class Identify(Base):
    __tablename__ = 'identify'
    file_id = sql.Column(sql.Integer, sql.ForeignKey('movie.file_id'), primary_key=True)
    output = sql.Column(sql.Text)
    moviefile = orm.relationship('MovieFile', backref=orm.backref('identify', uselist=False))


Usage = sql.Table(
    'usage', Base.metadata,
    sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id')),
    sql.Column('timestamp', sql.DateTime),
    sql.Column('time_', sql.Float))


Scrub = sql.Table(
    'scrub', Base.metadata,
    sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id')),
    sql.Column('start', sql.Float),
    sql.Column('end', sql.Float))
