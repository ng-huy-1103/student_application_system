document.addEventListener('DOMContentLoaded', function() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || 'No file chosen';
            const fileLabel = this.nextElementSibling;
            
            if (fileLabel && fileLabel.classList.contains('form-file-label')) {
                fileLabel.textContent = fileName;
            }
            
            if (e.target.files[0] && e.target.files[0].type.match('image.*')) {
                const reader = new FileReader();
                const previewId = `${this.id}-preview`;
                let preview = document.getElementById(previewId);
                
                if (!preview) {
                    preview = document.createElement('img');
                    preview.id = previewId;
                    preview.className = 'img-thumbnail mt-2';
                    preview.style.maxHeight = '200px';
                    this.parentNode.appendChild(preview);
                }
                
                reader.onload = function(e) {
                    preview.src = e.target.result;
                }
                
                reader.readAsDataURL(e.target.files[0]);
            }
        });
    });
    
    const form = document.querySelector('form');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    }
});
