"""Task View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest tests/test_task_views.py


from app import app
import os
from unittest import TestCase

from models import db, connect_db, Task, User

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


class TaskViewTestCase(TestCase):
    """Test views for tasks."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User(
            name='Janice',
            email="janice@gmail.com",
            slack_user_id="75",
            slack_team_id='ab43',
            slack_img_url='testimg2.com')
        self.testuser_id = 721
        self.testuser.id = self.testuser_id

        db.session.add(self.testuser)
        db.session.commit()

    def test_add_task(self):
        """Can we add a task?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of our test

            resp = c.post("api/tasks/new", json={"title": "Clean the garage"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            task = Task.query.one()
            self.assertEqual(task.title, "Clean the garage")

    def test_add_no_session(self):
        """ Do we get redirected if we are not logged in? """

        with self.client as c:
            resp = c.post(
                "api/tasks/new",
                data={
                    "title": "Clean the garage"},
                follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

    def test_add_invalid_user(self):
        """ Are we redirected if user is invalid? """

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = 99222224  # user does not exist

            resp = c.post(
                "api/tasks/new",
                data={
                    "title": "Clean the garage"},
                follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

    def test_task_show(self):
        """ Does the task show? """
        t = Task(
            id=12345,
            title="a test task",
            user_id=self.testuser_id
        )

        db.session.add(t)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            t = Task.query.get(12345)

            resp = c.get(f'/tasks/{t.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(t.title, str(resp.data))

    def test_invalid_task_show(self):
        """ Do invalid tasks return errors? """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            resp = c.get('/tasks/99999999')

            self.assertEqual(resp.status_code, 404)

    def test_task_delete(self):
        """ Can a task be deleted? """
        t = Task(
            id=12345,
            title="a test task",
            user_id=self.testuser_id
        )
        db.session.add(t)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['CURR_USER_KEY'] = self.testuser.id

            resp = c.get("api/tasks/12345/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            t = Task.query.get(12345)
            self.assertIsNone(t)

    def test_message_delete_no_authentication(self):
        """ Can any task be deleted without authentication? """
        t = Task(
            id=12345,
            title="a test task",
            user_id=self.testuser_id
        )
        db.session.add(t)
        db.session.commit()

        with self.client as c:
            resp = c.get("api/tasks/12345/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Sign in with Slack", str(resp.data))

            t = Task.query.get(12345)
            self.assertIsNotNone(t)
