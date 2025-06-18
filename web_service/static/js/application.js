document.addEventListener('DOMContentLoaded', function() {
    const saveEvaluationBtn = document.getElementById('saveEvaluation');
    
    if (saveEvaluationBtn) {
        saveEvaluationBtn.addEventListener('click', function() {
            const form = document.getElementById('evaluationForm');
            const formData = new FormData(form);
            const applicationId = window.location.pathname.split('/').pop();
            
            fetch(`/application/${applicationId}/evaluate`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success alert-dismissible fade show';
                    alertDiv.role = 'alert';
                    alertDiv.innerHTML = `
                        Evaluation saved successfully!
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    
                    form.parentNode.insertBefore(alertDiv, form);
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                    alertDiv.role = 'alert';
                    alertDiv.innerHTML = `
                        Error: ${data.error || 'Failed to save evaluation'}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    form.parentNode.insertBefore(alertDiv, form);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                alertDiv.role = 'alert';
                alertDiv.innerHTML = `
                    Error: ${error.message || 'Failed to save evaluation'}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                form.parentNode.insertBefore(alertDiv, form);
            });
        });
    }

    const languageToggle = document.getElementById('languageToggle');
    
    if (languageToggle) {
        languageToggle.addEventListener('change', function() {
            const englishContent = document.querySelectorAll('.english-content');
            const russianContent = document.querySelectorAll('.russian-content');
            
            if (this.checked) {
                englishContent.forEach(el => el.style.display = 'none');
                russianContent.forEach(el => el.style.display = 'block');
            } else {
                englishContent.forEach(el => el.style.display = 'block');
                russianContent.forEach(el => el.style.display = 'none');
            }
        });
    }
    
    const processBtn = document.getElementById('processDocuments');
    
    if (processBtn) {
        processBtn.addEventListener('click', function() {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            this.closest('form').submit();
        });
    }
});


