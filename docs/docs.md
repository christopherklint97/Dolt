# What is Dolt?
Dolt is a simple task manager that integrates with Slack through Oauth and slash commands.

## How to use Dolt?
The functionality of Dolt can be divided up into two different categories: [tasks](#tasks) and [groups](#groups).

### <a name="tasks"></a>Tasks
Tasks are the to-do items that you will be creating the most of in the app. There are two different ways for creating tasks. You can use the [web app](dolt.christopherklint.com) to create them or add the Dolt app to your Slack workspace and create tasks right in Slack.

When creating tasks, all you really need is a title to save a task. However, if your want to add more informatio, you can use the following optional paramters:
- Description
- Due date
- Group
- Importance

Try out the [web app](dolt.christopherklint.com) to get familiar with the different task options!

### <a name="groups"></a>Groups
Groups work as tags or collections to categorize tasks. They are very easy to use and only require a name when creating them.

## What is the Slack integration?
The Slack integration is composed of two different elements:
1. Logging into the web app with Slack using Oauth
2. Viewing and adding tasks and groups inside your Slack workspace with slash commands

### Oauth
Logging in with Slack is nothing that you need to stress about. It is simply a handy feature that syncs your tasks and groups with your Slack account.

### Slash commands
To get the most out of Dolt, you can access your tasks and groups from within Slack! Below are the slash commands that work with Dolt.

*Note: the Dolt app needs to be installed on your workspace in order for the commands to work!!*

## Slack slash commands
### View all open tasks
```code
/dolt 
```
Use this command to view all of tasks that are not marked as completed. You can filter the tasks by the following optional parameters:
- $due  
    - Filter tasks based on when the task is due. Replace the word *due* with *today*, *tomorrow*, or *later*.
- (group_name)
    - Filter tasks based on group. Replace *group_name* with the name of the group
- \*
    - Character for filtering the important tasks.

Example:
```code
/dolt $today (group1) *
```

### Add a new task
```code
/dolt.task "title"
```
Command for adding a new task. The only required parameter is the *title* parameter. The rest below are optional:
- \<description>
    - Add a description to the task. Replace *description* with the description.
- $due  
    - Add due date for the task. Replace the word *due* with the date formatted as YY-MM-DD. Task is due the same date as the day you added it by defaut.
- (group_name)
    - Add a group to the task. Replace *group_name* with the name of the group.
- \*
    - Character for marking the task as important.
Example:
```code
/dolt.task "Order pizza" <Do it before the fellas arrive> $20-11-23 (The Boys) *
```

### Add a new group
```code
/dolt.group group_name
```
Command for adding a new group. Parameter *group_name* is required.

### View all groups
```code
/dolt.groups
```
Command for viewing all groups. No parameters.