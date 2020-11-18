import requests
from models import db, connect_db, User, Task, Group
import os

from flask import Flask, render_template, request, flash, redirect, session, cli, url_for, g, jsonify
from flask_cors import CORS
from flask_debugtoolbar import DebugToolbarExtension

from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.web import WebClient
from slack_sdk.oauth.state_store import FileOAuthStateStore

from datetime import date, timedelta


app = Flask(__name__)

# Activate CORS for flask app
CORS(app)

# Load .env variables
cli.load_dotenv('.env')

# Issue and consume state parameter value on the server-side.
state_store = FileOAuthStateStore(expiration_seconds=300, base_dir="./data")


# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///dolt'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "secret123")
toolbar = DebugToolbarExtension(app)

connect_db(app)

db.create_all()

###############################################################################
# Before the requests


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if 'CURR_USER_KEY' in session:
        g.user = User.query.get(session['CURR_USER_KEY'])
    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session['CURR_USER_KEY'] = user.id
    flash(f"Hello, {user.name}!", "success")


def do_logout():
    """Logout user."""

    if 'CURR_USER_KEY' in session:
        del session['CURR_USER_KEY']
        del session['token']


######################################################################################
# Home, logging in, logging out

@app.route("/")
def homepage():
    """Show homepage."""

    if g.user:
        # handle the homepage view for a logged in user
        return redirect("/tasks")
    else:
        return render_template('login.html')


@app.route("/login")
def login():
    """Login."""

    # Generate a random value and store it on the server-side
    state = state_store.issue()

    # Build https://slack.com/oauth/v2/authorize with sufficient query parameters
    authorize_url_generator = AuthorizeUrlGenerator(
        client_id=os.environ.get("SLACK_CLIENT_ID", None),
        user_scopes=["identity.basic", "identity.email",
                     "identity.team", "identity.avatar"]
    )

    redirect_uri = authorize_url_generator.generate(state)

    return redirect(redirect_uri)


@app.route("/login/callback")
def login_callback():
    """Handle callback for the login."""

    # Retrieve the auth code from the request params
    if "code" in request.args:
        # Verify the state parameter
        if state_store.consume(request.args["state"]):
            client = WebClient()  # no prepared token needed for this
            # Complete the installation by calling oauth.v2.access API method
            oauth_response = client.oauth_v2_access(
                client_id=os.environ.get("SLACK_CLIENT_ID", None),
                client_secret=os.environ.get("SLACK_CLIENT_SECRET", None),
                code=request.args["code"]
            )

            # Check if the request to Slack API was successful
            if oauth_response['ok'] == True:
                # Saving access token for the authenticated user in the session
                token = oauth_response['authed_user']['access_token']
                session['token'] = token

                # Requesting the Slack identity of the user
                client = WebClient(token=token)
                user_response = client.api_call(
                    api_method='users.identity',
                )

                # Check if the request to Slack API was successful
                if user_response['ok'] == True:
                    # Search in db for matching user with Slack ID
                    slack_user_id = user_response['user']['id']
                    user = User.query.filter_by(
                        slack_user_id=slack_user_id).first() or None

                    # If user is found, login
                    if user:
                        do_login(user)

                    else:
                        # Add the information from Slack into the db
                        name = user_response['user']['name']
                        email = user_response['user']['email']
                        slack_team_id = user_response['team']['id']
                        slack_img_url = user_response['user']['image_512']

                        # Add user to the db
                        user = User(name=name, email=email,
                                    slack_user_id=slack_user_id, slack_team_id=slack_team_id, slack_img_url=slack_img_url)
                        db.session.add(user)
                        db.session.commit()

                        # Login new user
                        user = User.query.filter_by(
                            slack_user_id=slack_user_id).first()
                        do_login(user)

    return redirect(url_for('homepage'))


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    flash(f"You have been logged out.", "success")
    return redirect("/")

############################################################################################
# API functions

##################################################
# API tasks


@app.route('/api/tasks/new', methods=['POST'])
def new_task():
    """ Add new task for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    title = request.json['title']
    description = request.json['description']
    date = request.json['date'] or Task.due.default.arg
    if request.json['group'] == 'None':
        task = Task(title=title, description=description,
                    due=date, user_id=g.user.id)
    else:
        group = Group.query.filter_by(name=request.json['group']).first()
        task = Task(title=title, description=description,
                    due=date, group_id=group.id, user_id=g.user.id)

    # Add the new task
    db.session.add(task)
    db.session.commit()

    return redirect(request.path)


@app.route('/tasks')
def get_all_tasks():
    """ Return all tasks for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .all())

    return render_template('home.html', tasks=tasks, view='all', user=g.user)


@app.route('/tasks/important')
def get_important_tasks():
    """ Return important tasks for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter_by(important=True)
             .all())

    return render_template('home.html', tasks=tasks, view='important', user=g.user)


@app.route('/tasks/today')
def get_today_tasks():
    """ Return tasks due today for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due <= date.today().isoformat())
             .all())

    return render_template('home.html', tasks=tasks, view='today', user=g.user)


@app.route('/tasks/tomorrow')
def get_tomorrow_tasks():
    """ Return tasks due tomorrow for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due - timedelta(days=1) == date.today().isoformat())
             .all())

    return render_template('home.html', tasks=tasks, view='tomorrow', user=g.user)


@app.route('/tasks/later')
def get_later_tasks():
    """ Return tasks due later for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due - timedelta(days=2) >= date.today().isoformat())
             .all())

    return render_template('home.html', tasks=tasks, view='later', user=g.user)


@app.route('/groups/<int:group_id>')
def get_group_tasks(group_id):
    """ Return tasks in a group for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter_by(group_id=group_id)
             .all())

    return render_template('home.html', tasks=tasks, view=group_id, user=g.user)

##################################################
# API groups


@app.route('/api/groups/new', methods=['POST'])
def new_group():
    """ Add new group for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    name = request.json['name']

    # Add the new group
    group = Group(name=name, user_id=g.user.id)
    db.session.add(group)
    db.session.commit()

    return redirect(request.path)
