document.addEventListener('DOMContentLoaded', function() {
  const reviewForm = document.getElementById('review-form');
  if (!reviewForm) return;

  reviewForm.addEventListener('submit', function(event) {
    event.preventDefault();

    const decision = document.getElementById('decision').value;
    const comments = document.getElementById('comments').value;
    const score = document.getElementById('score').value;
    const applicationId = reviewForm.dataset.applicationId; 

    if (!decision) {
      alert('Please select a decision.');
      return;
    }
    if (score && (isNaN(score) || score < 0 || score > 100)) {
      alert('Score must be a number between 0 and 100.');
      return;
    }

    const formData = new URLSearchParams({
      decision: decision,
      comments: comments
    });

    if (score) {
      formData.append('score', score);
    }

    fetch(`/application/${applicationId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      const msgDiv = document.getElementById('review-message');
      if (data.success) {
        msgDiv.innerHTML = `<div class="alert alert-success">Review submitted successfully. New status: <strong>${data.new_status}</strong></div>`;
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else if (data.error) {
        msgDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
      } else {
        msgDiv.innerHTML = `<div class="alert alert-warning">Unexpected response from server.</div>`;
      }
    })
    .catch(() => {
      const msgDiv = document.getElementById('review-message');
      msgDiv.innerHTML = `<div class="alert alert-danger">Network or server error.</div>`;
    });
  });
});

