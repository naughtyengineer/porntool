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

class MovieFile(PornFile):
    __tablename__ = 'movie'
    id_ = sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id'), primary_key=True)
    last = sql.Column(sql.DateTime)

    girls = orm.relationship(
        'Girl', secondary=file_girl_association, backref=orm.backref('pornfiles'))

    __mapper_args__ = {
        'polymorphic_identity':'movie',
    }


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
        return '{}({}, {})'.format(self.__class__.__name__, self.hostname, self.path)

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


class Clip(Base):
    """tag subsections of movies for highlights"""
    __tablename__ = 'clip'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    file_id = sql.Column(sql.Integer, sql.ForeignKey('movie.file_id'))
    start = sql.Column(sql.Float)
    duration = sql.Column(sql.Float)

    moviefile = orm.relationship('MovieFile', backref=orm.backref('clips'))
    tags = orm.relationship(
        'Tag', secondary=clip_tag_association, backref=orm.backref('clips'))


class Flag(Base):
    """flag a location in a movie - probably because its good"""
    __tablename__ = 'flag'
    id_ = sql.Column('id', sql.Integer, primary_key=True)
    file_id = sql.Column(sql.Integer, sql.ForeignKey('movie.file_id'))
    location = sql.Column(sql.Float)
    moviefile = orm.relationship('MovieFile', backref=orm.backref('flags'))


Usage = sql.Table(
    'usage', Base.metadata,
    sql.Column('file_id', sql.Integer, sql.ForeignKey('file.id')),
    sql.Column('timestamp', sql.DateTime),
    sql.Column('time_', sql.Float))
