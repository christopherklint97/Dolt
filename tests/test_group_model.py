"""Group model tests."""

# run these tests like:
#
#    python -m unittest tests/test_group_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Group

# Use test database and don't clutter tests with SQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///dolt_test'
app.config['SQLALCHEMY_ECHO'] = False

# Make Flask errors be real errors, rather than HTML pages with error info
app.config['TESTING'] = True

# This is a bit of hack, but don't use Flask DebugToolbar
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Don't req CSRF for testing
app.config['WTF_CSRF_ENABLED'] = False


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class TaskModelTestCase(TestCase):
    """Test views for tasks."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        self.uid = 55
        u = User(
            name='John Appleseed',
            email="john@appleseed.com",
            slack_user_id="1234",
            slack_team_id='1234',
            slack_img_url='testing.com')
        u.id = self.uid
        db.session.add(u)
        db.session.commit()

        self.u = User.query.get(self.uid)

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_task_model(self):
        """Does basic model work?"""

        g = Group(
            name="Best group ever",
            user_id=self.uid
        )

        db.session.add(g)
        db.session.commit()

        # User should have 1 group
        self.assertEqual(len(self.u.groups), 1)
        self.assertEqual(self.u.groups[0].name, "Best group ever")
