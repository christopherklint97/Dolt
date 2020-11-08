import os

from flask import Flask, render_template, request, flash, redirect, session, cli
from flask_cors import CORS
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient

from models import db, connect_db

import requests

app = Flask(__name__)
CORS(app)

# Load .env variables
cli.load_dotenv('.env')

# User session management setup
# https://flask-login.readthedocs.io/en/latest
login_manager = LoginManager()
login_manager.init_app(app)

# OAuth 2 client setup
client = WebApplicationClient(os.environ.get('SLACK_CLIENT_ID', None))

# Flask-Login helper to retrieve a user from our db


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


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


@app.route("/")
def homepage():
    """Show homepage."""

    if current_user.is_authenticated:
        # handle the homepage view for a logged in user
        return render_template("home.html")
    else:
        return render_template('login.html')


@app.route("/login")
def login():
    """Login."""

    # Use oauth library to construct the request for Slack login and provide
    # scopes that let you retrieve user's profile from Slack
    request_uri = client.prepare_request_uri(
        'https://slack.com/oauth/v2/authorize',
        user_scope="identity.basic"
    )

    return redirect(request_uri)


@app.route("/login/callback")
def login_callback():
    """Handle callback for the login."""

    # The code parameter is an authorization code that you will exchange for a long-lived access token
    code = request.args.get("code")

    # Prepare and send a request to get tokens! Yay tokens!
    token_url = client.prepare_token_request(
        'https://slack.com/api/oauth.v2.access',
        code=code,
        client_id=os.environ.get('SLACK_CLIENT_ID', None),
        client_secret=os.environ.get('SLACK_CLIENT_SLACK', None)
    )

    token_response = requests.get(token_url)

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Now that you have tokens (yay) let's find and hit the URL
    # from Slack that gives you the user's profile information,
    userinfo_endpoint = 'https://slack.com/api/users.identity'
    uri = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri)

    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    # Create a user in your db with the information provided
    # by Google
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))

    return render_template("home.html")


@app.route("/logout")
@login_required
def logout():
    """Logout."""
    logout_user()
    return redirect("/")


# Adding SSL when running locally
if __name__ == "__main__":
    app.run(ssl_context="adhoc")
