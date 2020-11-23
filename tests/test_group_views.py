"""Group View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest tests/test_group_views.py


from app import app
import os
from unittest import TestCase

from models import db, connect_db, Task, Group, User

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


class GroupViewTestCase(TestCase):
    """Test views for groups."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User(name='Janice', email="janice@gmail.com",
                             slack_user_id="75", slack_team_id='ab43', slack_img_url='testimg2.com')
        self.testuser.id = 721

        db.session.add(self.testuser)
        db.session.commit()

    def test_add_group(self):
        """Can we add a group?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of our test

            resp = c.post("api/groups/new", json={"name": "Shopping list"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            group = Group.query.one()
            self.assertEqual(group.name, "Shopping list")

    def test_add_no_session(self):
        """ Do we get redirected if we are not logged in? """

        with self.client as c:
            resp = c.post("/api/groups/new",
                          data={"name": "Shopping list"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

    def test_add_invalid_user(self):
        """ Are we redirected if user is invalid? """

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = 99222224  # user does not exist

            resp = c.post("/api/groups/new",
                          data={"name": "Shopping list"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

    def test_group_show(self):
        """ Does the group show? """
        g = Group(
            id=246,
            name="Best group ever",
            user_id=self.testuser.id
        )

        db.session.add(g)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            g = Group.query.get(246)

            resp = c.get(f'/groups/{g.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(g.name, str(resp.data))

    def test_group_delete(self):
        """ Can a group be deleted? """
        g = Group(
            id=246,
            name="Best group ever",
            user_id=self.testuser.id
        )
        db.session.add(g)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            resp = c.get("/api/groups/246/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            g = Group.query.get(246)
            self.assertIsNone(g)

    def test_group_delete_no_authentication(self):
        """ Can any group be deleted without authentication? """
        g = Group(
            id=246,
            name="Best group ever",
            user_id=self.testuser.id
        )
        db.session.add(g)
        db.session.commit()

        with self.client as c:
            resp = c.get("/api/groups/246/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

            g = Group.query.get(246)
            self.assertIsNotNone(g)
