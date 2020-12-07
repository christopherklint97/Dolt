import requests
from models import db, connect_db, User, Task, Group
import os

from flask import Flask, render_template, request, flash, redirect, session, cli, url_for, g, jsonify, make_response
from flask_cors import CORS
from flask_debugtoolbar import DebugToolbarExtension

from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.web import WebClient
from slack_sdk.oauth.installation_store import FileInstallationStore, Installation
from slack_sdk.oauth.state_store import FileOAuthStateStore
from slack_sdk.signature import SignatureVerifier

from datetime import date, timedelta

app = Flask(__name__)

# Issue and consume state parameter value on the server-side.
state_store = FileOAuthStateStore(
    expiration_seconds=300, base_dir="./data")

# Persist installation data and lookup it by IDs.
installation_store = FileInstallationStore(base_dir="./data")

# Activate CORS for flask app
CORS(app)

# Load .env variables
cli.load_dotenv('.env')

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///dolt'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
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
    session['sort'] = 'recent'
    flash(f"Hello, {user.name}!", "success")


def do_logout():
    """Logout user."""

    if 'CURR_USER_KEY' in session:
        del session['CURR_USER_KEY']
        del session['sort']


##########################################################################
# Home, logging in, logging out, installing app

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

    # Build https://slack.com/oauth/v2/authorize with sufficient query
    # parameters
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
        if state_store.consume(request.args.get("state")):
            client = WebClient()  # no prepared token needed for this
            # Complete the installation by calling oauth.v2.access API method
            oauth_response = client.oauth_v2_access(
                client_id=os.environ.get("SLACK_CLIENT_ID", None),
                client_secret=os.environ.get("SLACK_CLIENT_SECRET", None),
                code=request.args.get("code")
            )

            # Check if the request to Slack API was successful
            if oauth_response['ok']:
                # Saving access token for the authenticated user as a variable
                token = oauth_response['authed_user']['access_token']

                # Requesting the Slack identity of the user
                client = WebClient(token=token)
                user_response = client.api_call(
                    api_method='users.identity',
                )

                # Check if the request to Slack API was successful
                if user_response['ok']:
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
                        user = User(
                            name=name,
                            email=email,
                            slack_user_id=slack_user_id,
                            slack_team_id=slack_team_id,
                            slack_img_url=slack_img_url)
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


@app.route("/slack/install", methods=["GET"])
def oauth_start():
    """ Install slack app. """

    # Build https://slack.com/oauth/v2/authorize with sufficient query parameters
    authorize_url_generator = AuthorizeUrlGenerator(
        client_id=os.environ["SLACK_CLIENT_ID"],
        scopes=["app_mentions:read", "channels:read", "chat:write", "commands", "im:read",
                "im:write", "incoming-webhook", "reminders:read", "reminders:write", "users:read"],
        user_scopes=["search:read"],
        redirect_uri='https://dolt.christopherklint.com/slack/install/callback'
    )

    # Generate a random value and store it on the server-side
    state = state_store.issue()

    # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
    url = authorize_url_generator.generate(state)

    return redirect(url)


@app.route("/slack/install/callback", methods=["GET"])
def oauth_callback():
    """ Handle callback for installing the app """

    # Retrieve the auth code and state from the request params
    if "code" in request.args:
        # Verify the state parameter
        if state_store.consume(request.args.get("state")):
            client = WebClient()  # no prepared token needed for this
            # Complete the installation by calling oauth.v2.access API method
            oauth_response = client.oauth_v2_access(
                client_id=os.environ.get("SLACK_CLIENT_ID", None),
                client_secret=os.environ.get("SLACK_CLIENT_SECRET", None),
                code=request.args["code"]
            )

            installed_enterprise = oauth_response.get("enterprise") or {}
            installed_team = oauth_response.get("team") or {}
            installer = oauth_response.get("authed_user") or {}
            incoming_webhook = oauth_response.get("incoming_webhook") or {}
            bot_token = oauth_response.get("access_token")
            # NOTE: As oauth.v2.access doesn't include bot_id in response,
            # we call bots.info for storing the installation data along with bot_id.
            bot_id = None
            if bot_token is not None:
                auth_test = client.auth_test(token=bot_token)
                bot_id = auth_test["bot_id"]

            # Build an installation data
            installation = Installation(
                app_id=oauth_response.get("app_id"),
                enterprise_id=installed_enterprise.get("id"),
                team_id=installed_team.get("id"),
                bot_token=bot_token,
                bot_id=bot_id,
                bot_user_id=oauth_response.get("bot_user_id"),
                bot_scopes=oauth_response.get(
                    "scope"),  # comma-separated string
                user_id=installer.get("id"),
                user_token=installer.get("access_token"),
                user_scopes=installer.get("scope"),  # comma-separated string
                incoming_webhook_url=incoming_webhook.get("url"),
                incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
                incoming_webhook_configuration_url=incoming_webhook.get(
                    "configuration_url"),
            )
            # Store the installation
            installation_store.save(installation)

            return redirect(url_for('homepage'))
        else:
            return make_response(f"Try the installation again (the state value is already expired)", 400)

    error = request.args["error"] if "error" in request.args else ""
    return make_response(f"Something is wrong with the installation (error: {error})", 400)

##########################################################################
# API functions

##################################################
# API tasks


@app.route('/api/tasks/new', methods=['POST'])
def new_task():
    """ Add new task for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    title = request.json.get('title')
    description = request.json.get('description')
    date = request.json.get('date') or Task.due.default.arg
    if not request.json.get('group'):
        task = Task(title=title, description=description,
                    due=date, user_id=g.user.id)
    else:
        group = Group.query.filter_by(name=request.json.get('group')).first()
        task = Task(title=title, description=description,
                    due=date, group_id=group.id, user_id=g.user.id)

    # Add the new task
    db.session.add(task)
    db.session.commit()

    return redirect('/')


@app.route('/api/tasks/<int:task_id>/edit', methods=['POST'])
def edit_task_submit(task_id):
    """ Submit updated task for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    title = request.form.get('title')
    description = request.form.get('description')
    date = request.form.get('date')

    # Add the new task
    task = Task.query.get_or_404(task_id)
    task.title = title
    task.description = description
    task.date = date
    if request.form['group'] != 'None':
        group = Group.query.filter_by(name=request.form['group']).first()
        task.group_id = group.id
    else:
        task.group_id = None

    db.session.add(task)
    db.session.commit()

    return redirect('/')


@app.route('/api/tasks/important', methods=['POST'])
def star_task():
    """ Add star to task for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    id = request.json.get('id')

    # Update the task depending on important status
    task = Task.query.get_or_404(id)
    if not task.important:
        task.important = True
    else:
        task.important = False

    db.session.add(task)
    db.session.commit()

    return redirect('/tasks/important')


@app.route('/api/tasks/completed', methods=['POST'])
def complete_task():
    """ Complete task for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    id = request.json.get('id')

    # Update the task depending on important status
    task = Task.query.get_or_404(id)
    if not task.completed:
        task.completed = True
    else:
        task.completed = False

    db.session.add(task)
    db.session.commit()

    return redirect('/tasks/completed')


@app.route('/tasks')
def get_all_tasks():
    """ Return all tasks for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='all',
        user=g.user,
        sort=sort)


@app.route('/tasks/important')
def get_important_tasks():
    """ Return important tasks for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter_by(important=True)
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='important',
        user=g.user,
        sort=sort)


@app.route('/tasks/completed')
def get_completed_tasks():
    """ Return completed tasks for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter_by(completed=True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='completed',
        user=g.user,
        sort=sort)


@app.route('/tasks/today')
def get_today_tasks():
    """ Return tasks due today for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due <= date.today().isoformat())
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='today',
        user=g.user,
        sort=sort)


@app.route('/tasks/tomorrow')
def get_tomorrow_tasks():
    """ Return tasks due tomorrow for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due - timedelta(days=1) == date.today().isoformat())
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='tomorrow',
        user=g.user,
        sort=sort)


@app.route('/tasks/later')
def get_later_tasks():
    """ Return tasks due later for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter(Task.due - timedelta(days=2) >= date.today().isoformat())
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view='later',
        user=g.user,
        sort=sort)


@app.route('/groups/<int:group_id>')
def get_group_tasks(group_id):
    """ Return tasks in a group for current user"""
    if not g.user:
        return redirect("/")

    tasks = (Task
             .query
             .filter_by(user_id=g.user.id)
             .filter_by(group_id=group_id)
             .filter(Task.completed != True)
             .all())

    sort = session.get('sort') or 'recent'

    return render_template(
        'home.html',
        tasks=tasks,
        view=group_id,
        user=g.user,
        sort=sort)


@app.route('/tasks/<int:task_id>')
def edit_task(task_id):
    """ Show task details for current user"""
    if not g.user:
        return redirect("/")

    task = Task.query.get_or_404(task_id)

    return render_template('edit_task.html', task=task, user=g.user)


@app.route('/api/tasks/<int:task_id>/delete')
def delete_task(task_id):
    """ Delete task for signed in user """
    if not g.user:
        return redirect("/")

    task = Task.query.get_or_404(task_id)

    db.session.delete(task)
    db.session.commit()

    return redirect('/')


##################################################
# API groups


@app.route('/api/groups/new', methods=['POST'])
def new_group():
    """ Add new group for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    name = request.json.get('name')

    # Add the new group
    group = Group(name=name, user_id=g.user.id)
    db.session.add(group)
    db.session.commit()

    return redirect('/')


@app.route('/groups/<int:group_id>/edit')
def edit_group(group_id):
    """ Edit group for signed in user """
    if not g.user:
        return redirect("/")

    group = Group.query.get_or_404(group_id)

    return render_template('edit_group.html', group=group, user=g.user)


@app.route('/api/groups/<int:group_id>/edit', methods=['POST'])
def edit_group_submit(group_id):
    """ Update edited group name for signed in user """
    if not g.user:
        return redirect("/")

    # Handle AJAX request from client
    name = request.form.get('group-name')

    # Add the updated group
    group = Group.query.get_or_404(group_id)
    group.name = name
    db.session.add(group)
    db.session.commit()

    return redirect(f'/groups/{group_id}')


@app.route('/api/groups/<int:group_id>/delete')
def delete_group(group_id):
    """ Delete group for signed in user """
    if not g.user:
        return redirect("/")

    group = Group.query.get_or_404(group_id)

    db.session.delete(group)
    db.session.commit()

    return redirect('/')

##################################################
# API sorting


@app.route('/api/sort/<sort>')
def sort_tasks(sort):
    """ Sort tasks by the sorting option """
    if not g.user:
        return redirect("/")

    session['sort'] = sort

    return redirect('/')

##########################################################################
# Slack slash commands


def confirm_receipt():
    return ('', 200)


@app.route('/slack/tasks', methods=['POST'])
def slack_get_tasks():
    """ Get all open tasks for the slack user """

    # Confirm receipt to Slack so that no error is shown to user
    confirm_receipt()

    # Verify that the request actually came from Slack through its signature
    signature = SignatureVerifier(os.environ.get('SLACK_SIGNING_SECRET'))
    if not signature.is_valid_request(
            request.get_data(
                as_text=True),
            request.headers):
        return jsonify(
            response_type='ephemeral',
            text="Sorry, slash commando, that didn't work. Please try again.",
        )

    try:
        # in the case where this app gets a request from an Enterprise Grid workspace
        enterprise_id = request.form.get("enterprise_id")
        # The workspace's ID
        team_id = request.form["team_id"]
        # Lookup the stored bot token for this workspace
        bot = installation_store.find_bot(
            enterprise_id=enterprise_id,
            team_id=team_id,
        )
        bot_token = bot.bot_token if bot else None
        if not bot_token:
            # The app may be uninstalled or be used in a shared channel
            return make_response("Please install this app first!", 200)

        # Given the slack user id, extract the user and needed data
        slack_user_id = request.form.get('user_id')
        text = request.form.get('text')
        user = User.query.filter_by(slack_user_id=slack_user_id).first()

        # Declare variables to be used for filtering the tasks based on the slack
        # message
        due_tasks = None
        group_tasks = None
        important_tasks = None

        # Find all tasks due according to parameter
        if text.find('$') != -1:
            due = text.partition('$')[2].partition(' ')[0]

            if due.lower() == 'today':
                due_tasks = (Task
                             .query
                             .filter_by(user_id=user.id)
                             .filter(Task.due <= date.today().isoformat())
                             .filter(Task.completed != True)
                             .all())

            if due.lower() == 'tomorrow':
                due_tasks = (
                    Task .query .filter_by(
                        user_id=user.id) .filter(
                        Task.due -
                        timedelta(
                            days=1) == date.today().isoformat()) .filter(
                        Task.completed != True) .all())

            if due.lower() == 'later':
                due_tasks = (
                    Task .query .filter_by(
                        user_id=user.id) .filter(
                        Task.due -
                        timedelta(
                            days=2) >= date.today().isoformat()) .filter(
                        Task.completed != True) .all())

        # Find all tasks in group according to parameter
        if text.find('(') != -1:
            group = text.partition('(')[2].partition(')')[0]

            group_tasks = (Task
                           .query
                           .filter_by(user_id=user.id)
                           .filter(Task.group == group)
                           .filter(Task.completed != True)
                           .all())

        # Find all important tasks according to parameter
        if text.find('*') != -1:

            important_tasks = (Task
                               .query
                               .filter_by(user_id=user.id)
                               .filter(Task.important)
                               .filter(Task.completed != True)
                               .all())

        # Fetch final tasks based on parameters
        tasks = set()
        if due_tasks is not None:
            for task in due_tasks:
                tasks.add(task)

        if group_tasks is not None:
            for task in group_tasks:
                tasks.add(task)

        if important_tasks is not None:
            for task in important_tasks:
                tasks.add(task)

        if len(tasks) == 0:
            tasks = (Task
                     .query
                     .filter_by(user_id=user.id)
                     .filter(Task.completed != True)
                     .all())

        # Construct the blocks for the slack message
        blocks = [
            {
                "type": "header",
                "text": {
                        "type": "plain_text",
                        "text": "Here are all of your open tasks",
                        "emoji": True
                }
            },
            {
                "type": "divider"
            }
        ]

        # Loop through the tasks and add them to the blocks
        for task in tasks:
            dict_task = {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"{task.title}",
                    "emoji": True
                }
            }
            blocks.append(dict_task)

        # If there are no tasks, send a standard message
        if len(blocks) == 2:
            blocks = [{"type": "section", "text": {"type": "mrkdwn",
                                                   "text": "You currently have no open tasks. Nice work! :thumbsup:"}}]

        return jsonify(
            response_type='in_channel',
            blocks=blocks,
        )
    except Exception as e:
        print(e)

        # Indicate unsupported request patterns
        return make_response("", 404)


@app.route('/slack/tasks/new', methods=['POST'])
def slack_add_task():
    """ Add new task for the slack user """

    # Confirm receipt to Slack so that no error is shown to user
    confirm_receipt()

    # Verify that the request actually came from Slack through its signature
    signature = SignatureVerifier(os.environ.get('SLACK_SIGNING_SECRET'))
    if not signature.is_valid_request(
            request.get_data(
                as_text=True),
            request.headers):
        return jsonify(
            response_type='ephemeral',
            text="Sorry, slash commando, that didn't work. Please try again.",
        )

    # in the case where this app gets a request from an Enterprise Grid workspace
    enterprise_id = request.form.get("enterprise_id")
    # The workspace's ID
    team_id = request.form["team_id"]
    # Lookup the stored bot token for this workspace
    bot = installation_store.find_bot(
        enterprise_id=enterprise_id,
        team_id=team_id,
    )
    bot_token = bot.bot_token if bot else None
    if not bot_token:
        # The app may be uninstalled or be used in a shared channel
        return make_response("Please install this app first!", 200)

    # Given the slack user id, extract the user and needed data
    slack_user_id = request.form.get('user_id')
    text = request.form.get('text')
    user = User.query.filter_by(slack_user_id=slack_user_id).first()

    try:
        # Declare optional variables to be used for the new task based on the
        # slack message
        description = None
        due = Task.due.default.arg
        important = Task.important.default.arg
        group_name = None

        # Parse the title from the slack text
        title = text.partition('"')[2].partition('"')[0]

        # Parse the description from the slack text
        if text.find('<') != -1:
            description = text.partition('<')[2].partition('>')[0]

        # Parse the due date from the slack text
        if text.find('$') != -1:
            due = text.partition('$')[2].partition(' ')[0]

        # Parse with the task is important from the slack text
        if text.find('*') != -1:
            important = True

        # Parse the group from the slack text
        if text.find('(') != -1:
            group_name = text.partition('(')[2].partition(')')[0]

        # Add the task depending on the group
        if group_name is None:
            task = Task(title=title, description=description,
                        due=due, important=important, user_id=user.id)
        else:
            group = Group.query.filter_by(name=group_name).first()
            task = Task(title=title, description=description,
                        due=due, group_id=group.id, user_id=user.id)

        # Add the new task
        db.session.add(task)
        db.session.commit()

        # Success blocks
        blocks = [{"type": "section", "text": {"type": "mrkdwn",
                                               "text": "Success! Your new task is added, now get to work :muscle:"}}]

    except Exception as e:

        print(e)

        # Failed blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Sorry, something went wrong :worried: Please check your parameters and try again!"
                }
            }
        ]

    return jsonify(
        response_type='in_channel',
        blocks=blocks,
    )


@app.route('/slack/groups', methods=['POST'])
def slack_get_groups():
    """ Get all groups for the slack user """

    # Confirm receipt to Slack so that no error is shown to user
    confirm_receipt()

    # Verify that the request actually came from Slack through its signature
    signature = SignatureVerifier(os.environ.get('SLACK_SIGNING_SECRET'))
    if not signature.is_valid_request(
            request.get_data(
                as_text=True),
            request.headers):
        return jsonify(
            response_type='ephemeral',
            text="Sorry, slash commando, that didn't work. Please try again.",
        )

    # in the case where this app gets a request from an Enterprise Grid workspace
    enterprise_id = request.form.get("enterprise_id")
    # The workspace's ID
    team_id = request.form["team_id"]
    # Lookup the stored bot token for this workspace
    bot = installation_store.find_bot(
        enterprise_id=enterprise_id,
        team_id=team_id,
    )
    bot_token = bot.bot_token if bot else None
    if not bot_token:
        # The app may be uninstalled or be used in a shared channel
        return make_response("Please install this app first!", 200)

    # Given the slack user id, extract the user and needed data
    slack_user_id = request.form.get('user_id')
    user = User.query.filter_by(slack_user_id=slack_user_id).first()

    # Fetch all groups for slack user
    groups = (Group
              .query
              .filter_by(user_id=user.id)
              .all())

    # Construct the blocks for the slack message
    blocks = [
        {
            "type": "header",
            "text": {
                    "type": "plain_text",
                    "text": "Here are all of your groups",
                    "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]

    # Loop through the tasks and add them to the blocks
    for group in groups:
        dict_group = {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": f"{group.name}",
                "emoji": True
            }
        }
        blocks.append(dict_group)

    # If there are no groups, send a standard message
    if len(blocks) == 2:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You currently have no groups. Feel free to create one with /dolt.group :pray:"
                }
            }
        ]

    return jsonify(
        response_type='in_channel',
        blocks=blocks,
    )


@app.route('/slack/groups/new', methods=['POST'])
def slack_add_group():
    """ Add new group for the slack user """

    # Confirm receipt to Slack so that no error is shown to user
    confirm_receipt()

    # Verify that the request actually came from Slack through its signature
    signature = SignatureVerifier(os.environ.get('SLACK_SIGNING_SECRET'))
    if not signature.is_valid_request(
            request.get_data(
                as_text=True),
            request.headers):
        return jsonify(
            response_type='ephemeral',
            text="Sorry, slash commando, that didn't work. Please try again.",
        )

    # in the case where this app gets a request from an Enterprise Grid workspace
    enterprise_id = request.form.get("enterprise_id")
    # The workspace's ID
    team_id = request.form["team_id"]
    # Lookup the stored bot token for this workspace
    bot = installation_store.find_bot(
        enterprise_id=enterprise_id,
        team_id=team_id,
    )
    bot_token = bot.bot_token if bot else None
    if not bot_token:
        # The app may be uninstalled or be used in a shared channel
        return make_response("Please install this app first!", 200)

    # Given the slack user id, extract the user and needed data
    slack_user_id = request.form.get('user_id')
    text = request.form.get('text')
    user = User.query.filter_by(slack_user_id=slack_user_id).first()

    try:
        # Add the new group
        group = Group(name=text, user_id=user.id)
        db.session.add(group)
        db.session.commit()

        # Success blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Success! Your new group is added. Start adding tasks to it with /dolt.task :pencil:"
                }
            }
        ]

    except Exception as e:

        print(e)

        # Failed blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Sorry, something went wrong :worried: Please check your parameters and try again!"
                }
            }
        ]

    return jsonify(
        response_type='in_channel',
        blocks=blocks,
    )
