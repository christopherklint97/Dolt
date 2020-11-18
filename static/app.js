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

    // Send the new task to backend API
    await axios.post('/api/tasks/new', {
        title,
        description,
        date,
        group
    });

    // Resetting of form values on submit
    $('#new-task-title').val('');
    $('#new-task-description').val('');
    $('#datepicker').val('');
    $('#new-task-group').val('');

    location.reload();
}

/* Handle submission of the add group form */
async function addNewGroup(e) {
    e.preventDefault();

    const name = $('#new-group-name').val();

    // Send the new group to backend API
    await axios.post('/api/groups/new', { name });

    // Resetting of form values on submit
    $('#new-group-name').val('');

    location.reload();
}

/* Hide all of the new task fields */
function hideNewTaskFields(e) {

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
    const addGroupModal = $('#new-group-modal');
    const addGroupForm = $('#add-group-form');

    // Submit event for new tasks
    newTaskForm.on('submit', addNewTask);

    // Focus and click events for showing and hiding new task fields
    newTaskTitle.on('focus', showNewTaskFields);
    app.on('click', hideNewTaskFields);
    cancelBtn.on('click', hideNewTaskFields);

    // Implement add group modal on click
    addGroupModal.on('show.bs.modal', function () {
        $('#new-group-name').trigger('focus');
    });

    // Submit event for new groups
    addGroupForm.on('submit', addNewGroup);
}

addEventListeners();