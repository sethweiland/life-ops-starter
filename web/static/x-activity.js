function approveCandidate(date, candidateId) {
    var card = document.getElementById('body-' + candidateId).closest('.x-card');
    var bodyEl = document.getElementById('body-' + candidateId);
    var statusEl = document.getElementById('status-' + candidateId);
    var approveBtn = card.querySelector('.btn-approve-x');
    var skipBtn = card.querySelector('.btn-skip');

    approveBtn.disabled = true;
    if (skipBtn) skipBtn.disabled = true;
    approveBtn.textContent = 'Saving…';

    fetch('/x/api/candidates/' + encodeURIComponent(date) + '/approve/' + encodeURIComponent(candidateId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': lifeOpsCsrfToken() },
        body: JSON.stringify({ body: bodyEl.value }),
    })
    .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
    .then(function(res) {
        if (res.data.success) {
            statusEl.innerHTML = '<div class="x-msg ok">Approved — Your agent can post this. Not sent to X.</div>';
            markResolved(card, bodyEl, 'approved', 'Approved');
        } else {
            statusEl.innerHTML = '<div class="x-msg err">' + escapeHtml(res.data.error || 'Approve failed') + '</div>';
            approveBtn.disabled = false;
            if (skipBtn) skipBtn.disabled = false;
            approveBtn.textContent = 'Approve';
        }
    })
    .catch(function(err) {
        statusEl.innerHTML = '<div class="x-msg err">Request failed: ' + escapeHtml(String(err)) + '</div>';
        approveBtn.disabled = false;
        if (skipBtn) skipBtn.disabled = false;
        approveBtn.textContent = 'Approve';
    });
}

function skipCandidate(date, candidateId) {
    var card = document.getElementById('body-' + candidateId).closest('.x-card');
    var bodyEl = document.getElementById('body-' + candidateId);
    var statusEl = document.getElementById('status-' + candidateId);
    var approveBtn = card.querySelector('.btn-approve-x');
    var skipBtn = card.querySelector('.btn-skip');

    if (approveBtn) approveBtn.disabled = true;
    skipBtn.disabled = true;
    skipBtn.textContent = 'Skipping…';

    fetch('/x/api/candidates/' + encodeURIComponent(date) + '/skip/' + encodeURIComponent(candidateId), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': lifeOpsCsrfToken() },
        body: JSON.stringify({}),
    })
    .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
    .then(function(res) {
        if (res.data.success) {
            statusEl.innerHTML = '<div class="x-msg info">Skipped</div>';
            markResolved(card, bodyEl, 'skipped', 'Skipped');
        } else {
            statusEl.innerHTML = '<div class="x-msg err">Failed to skip</div>';
            if (approveBtn) approveBtn.disabled = false;
            skipBtn.disabled = false;
            skipBtn.textContent = 'Skip';
        }
    })
    .catch(function() {
        statusEl.innerHTML = '<div class="x-msg err">Request failed</div>';
        if (approveBtn) approveBtn.disabled = false;
        skipBtn.disabled = false;
        skipBtn.textContent = 'Skip';
    });
}

function markResolved(card, bodyEl, status, label) {
    card.classList.remove('candidate-pending');
    card.classList.add('candidate-' + status);
    var badge = card.querySelector('.candidate-status-badge');
    badge.textContent = label;
    badge.className = 'candidate-status-badge ' + status;
    bodyEl.disabled = true;
    card.querySelector('.candidate-actions').innerHTML = '';
}

function escapeHtml(text) {
    if (!text) return '';
    var el = document.createElement('span');
    el.textContent = text;
    return el.innerHTML;
}

document.querySelectorAll('[data-draft-action]').forEach(function(button) {
    button.addEventListener('click', function() {
        var card = button.closest('.x-card');
        var action = button.dataset.draftAction;
        if (action === 'approve') approveCandidate(button.dataset.date, card.dataset.id);
        if (action === 'skip') skipCandidate(button.dataset.date, card.dataset.id);
    });
});
document.querySelectorAll('[data-date-filter]').forEach(function(input) {
    input.addEventListener('change', function() { input.form.requestSubmit(); });
});

