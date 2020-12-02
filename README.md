# Live demo

To see live demo deployed on Heroku, visit [here](https://dolt.christopherklint.com/).

# What is Dolt?

Dolt is a task manager that is integrated with Slack through Oauth login functionality and slash commands for viewing adding tasks and groups.

I chose these features because I wanted to keep the web app fast and simple while still allowing for great practicality from a Slack workspace.

# Standard user flow of Dolt

Here are a step by step overview of the user flow for the app:

1. Arrive at the homepage and sign in with Slack
2. Login successful, reach the task manager dashboard
3. Create tasks with different attributes
4. Add these tasks to a group (user could have also created the groups first)
5. After getting familiar with the web app, user installs the Dolt app to their Slack workspace
6. User learns the slash commands
7. User can now view and add both tasks and groups with the right commands

# API used

[Slack API](https://api.slack.com/)

# Technology stack

- Flask-Python
- Postgresql
- SQL Alchemy
- Unit testing
- Axios.js
- jQuery
- Bootstrap
- Popper.js
- Jinja

# Docs

More docs for how to use Dolt can be found [here](https://github.com/christopherklint97/Dolt/blob/main/docs/docs.md)
