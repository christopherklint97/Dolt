"""SQLAlchemy models for Dolt."""

import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """ Users in the app """

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        nullable=False
    )

    slack_user_id = db.Column(
        db.Text,
        nullable=False
    )

    slack_team_id = db.Column(
        db.Text,
        nullable=False
    )

    slack_img_url = db.Column(
        db.String(),
        nullable=False
    )

    def get_firstname(self):
        return name.partition(' ')[0]


class Task(db.Model):
    """ Tasks are to-do items """

    __tablename__ = 'tasks'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    title = db.Column(
        db.Text,
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    due = db.Column(
        db.DateTime,
    )

    reminder = db.Column(
        db.DateTime,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )

    user = db.relationship('User', backref='tasks')


class Group(db.Model):
    """ Group of tasks used for sorting """

    __tablename__ = 'groups'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(20),
        nullable=False
    )

    description = db.Column(
        db.Text
    )


class Group_Task(db.Model):
    """ Assigning the tasks to each group """

    __tablename__ = 'groups_tasks'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    group_id = db.Column(
        db.Integer,
        db.ForeignKey('groups.id')
    )

    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id')
    )

    group = db.relationship('Group', backref='groups_tasks')
    task = db.relationship('Task', backref='groups_tasks')


def connect_db(app):
    """Connect this database to provided Flask app.
    """

    db.app = app
    db.init_app(app)
