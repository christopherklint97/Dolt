/* Datepicker from jQuery UI */
$(function () {
  $("#datepicker").datepicker({
    dateFormat: "yy-mm-dd",
  });
});

/* Enable tooltips everywhere */
$(function () {
  $('[data-toggle="tooltip"]').tooltip();
});

/* Handle submission of the new task form */
async function addNewTask(e) {
  e.preventDefault();

  const title = $("#new-task-title").val();
  const description = $("#new-task-description").val();
  const date = $("#datepicker").val();
  const group = $("#new-task-group").val();

  // Send the new task to backend API
  await axios.post("/api/tasks/new", {
    title,
    description,
    date,
    group,
  });

  // Resetting of form values on submit
  $("#new-task-title").val("");
  $("#new-task-description").val("");
  $("#datepicker").val("");
  $("#new-task-group").val("");

  location.reload();
}

/* Handle submission of the add group form */
async function addNewGroup(e) {
  e.preventDefault();

  const name = $("#new-group-name").val();

  // Send the new group to backend API
  await axios.post("/api/groups/new", { name });

  // Resetting of form values on submit
  $("#new-group-name").val("");

  location.reload();
}

/* Hide all of the new task fields */
function hideNewTaskFields(e) {
  if (
    e.target.tagName !== "INPUT" &&
    e.target.tagName !== "SELECT" &&
    e.target.tagName !== "TEXTAREA"
  ) {
    const newTaskFields = $("#new-task-fields");
    newTaskFields.hide();
  }
}

/* Show the new task fields on focus */
function showNewTaskFields() {
  const newTaskFields = $("#new-task-fields");
  newTaskFields.show();
}

/* Star task and send to API */
async function starTask(e) {
  e.preventDefault();

  id = e.currentTarget.attributes[1].value;

  await axios.post("/api/tasks/important", { id });

  location.reload();
}

/* Sort tasks in API and refresh */
async function sortTasks(e) {
  e.preventDefault();

  url = e.currentTarget.attributes[1].value;

  await axios.get(url);

  location.reload();
}

/* Complete tasks in API and refresh */
async function completeTasks(e) {
  e.preventDefault();

  console.log(e);

  id = e.currentTarget.attributes[1].value;

  await axios.post("/api/tasks/completed", { id });

  location.reload();
}

/* Collection of all the event listeners */
function addEventListeners() {
  const newTaskForm = $("#new-task-form");
  const newTaskTitle = $("#new-task-title");
  const app = $("#app");
  const cancelBtn = $("#cancel-btn");
  const addGroupModal = $("#new-group-modal");
  const addGroupForm = $("#add-group-form");
  const star = $("[data-star]");
  const sort = $(".sort");
  const check = $(".check");

  // Submit event for new tasks
  newTaskForm.on("submit", addNewTask);

  // Focus and click events for showing and hiding new task fields
  newTaskTitle.on("focus", showNewTaskFields);
  app.on("click", hideNewTaskFields);
  cancelBtn.on("click", hideNewTaskFields);

  // Implement add group modal on click
  addGroupModal.on("show.bs.modal", function () {
    $(".edit-group-name").trigger("focus");
  });

  // Submit event for new groups
  addGroupForm.on("submit", addNewGroup);

  // Change importance for the task
  star.on("click", starTask);

  // Sort tasks based on backend API
  sort.on("click", sortTasks);

  // Complete tasks by checking them
  check.on("click", completeTasks);
}

addEventListeners();
