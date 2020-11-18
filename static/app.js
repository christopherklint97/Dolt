/* Datepicker from jQuery UI */
$(function () {
    $("#datepicker").datepicker({
        dateFormat: "yy-mm-dd"
    });
});

/* Handle submission of the new task form */
async function addNewTask(e) {
    e.preventDefault();

    const title = $('#new-task-title').val();
    const description = $('#new-task-description').val();
    const date = $('#datepicker').val();
    const group = $('#new-task-group').val();

    // Resetting of form values on submit
    $('#new-task-title').val('');
    $('#new-task-description').val('');
    $('#datepicker').val('');
    $('#new-task-group').val('');

    // Send the new task to backend API
    await axios.post('/api/task/new', {
        title,
        description,
        date,
        group
    });
}

/* Hide all of the new task fields */
function hideNewTaskFields(e) {
    console.log(e)

    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT' && e.target.tagName !== 'TEXTAREA') {
        const newTaskFields = $('#new-task-fields');
        newTaskFields.hide();
    }
}

/* Show the new task fields on focus */
function showNewTaskFields() {
    const newTaskFields = $('#new-task-fields');
    newTaskFields.show();
}

/* Collection of all the event listeners */
function addEventListeners() {
    const newTaskForm = $('#new-task-form');
    const newTaskTitle = $('#new-task-title');
    const app = $('#app');
    const cancelBtn = $('#cancel-btn');
    const addGroup = $('#new-group-modal')

    // Submit event for new tasks
    newTaskForm.on('submit', addNewTask);

    // Focus and click events for showing and hiding new task fields
    newTaskTitle.on('focus', showNewTaskFields);
    app.on('click', hideNewTaskFields);
    cancelBtn.on('click', hideNewTaskFields);

    // Implement add group modal on click
    addGroup.on('show.bs.modal', function () {
        $('#new-group-name').trigger('focus');
    });
}

addEventListeners();