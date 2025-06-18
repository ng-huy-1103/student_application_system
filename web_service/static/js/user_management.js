document.addEventListener('DOMContentLoaded', function() {
    const editUserModal = document.getElementById('editUserModal');
    if (editUserModal) {
        editUserModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            const email = button.getAttribute('data-email');
            const firstName = button.getAttribute('data-first-name');
            const lastName = button.getAttribute('data-last-name');
            const role = button.getAttribute('data-role');
            const isActive = button.getAttribute('data-is-active') === 'True';
            const userIdInput = editUserModal.querySelector('#edit_user_id');
            const usernameInput = editUserModal.querySelector('#edit_username');
            const emailInput = editUserModal.querySelector('#edit_email');
            const firstNameInput = editUserModal.querySelector('#edit_first_name');
            const lastNameInput = editUserModal.querySelector('#edit_last_name');
            const roleSelect = editUserModal.querySelector('#edit_role');
            const isActiveCheckbox = editUserModal.querySelector('#edit_is_active');
            
            userIdInput.value = userId;
            usernameInput.value = username;
            emailInput.value = email;
            firstNameInput.value = firstName;
            lastNameInput.value = lastName;
            roleSelect.value = role;
            isActiveCheckbox.checked = isActive;
            
            if (username === 'admin') {
                usernameInput.disabled = true;
                roleSelect.disabled = true;
            } else {
                usernameInput.disabled = false;
                roleSelect.disabled = false;
            }
        });
    }
    
    const deleteUserModal = document.getElementById('deleteUserModal');
    if (deleteUserModal) {
        deleteUserModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            const userIdInput = deleteUserModal.querySelector('#delete_user_id');
            const usernameSpan = deleteUserModal.querySelector('#delete_username');
            userIdInput.value = userId;
            usernameSpan.textContent = username;
        });
    }
});
