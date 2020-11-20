"""SQLAlchemy models for Dolt."""

from datetime import date, datetime

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
        db.Date,
        default=date.today().isoformat()
    )

    important = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now(),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )

    group_id = db.Column(
        db.Integer,
        db.ForeignKey('groups.id')
    )

    user = db.relationship('User', backref='tasks')
    group = db.relationship('Group', backref='tasks')


class Group(db.Model):
    """ Group of tasks used for sorting """

    __tablename__ = 'groups'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(50),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )

    user = db.relationship('User', backref='groups')


def connect_db(app):
    """Connect this database to provided Flask app.
    """

    db.app = app
    db.init_app(app)
