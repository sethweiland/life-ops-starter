// Folders nav — native <details>; JS adds click-away / Escape

function lifeOpsCsrfToken() {
    var token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.content : '';
}

function initNavFolders() {
    var root = document.querySelector("[data-nav-folders]");
    if (!root) return;
    var toggle = root.querySelector("[data-nav-folders-toggle]");

    function isOpen() {
        return !!root.open;
    }

    function setOpen(open) {
        root.open = !!open;
    }

    document.addEventListener("click", function(event) {
        if (!root.contains(event.target)) {
            setOpen(false);
        }
    });

    document.addEventListener("keydown", function(event) {
        if (event.key === "Escape" && isOpen()) {
            setOpen(false);
            if (toggle) toggle.focus();
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initNavFolders);
} else {
    initNavFolders();
}

// Broken optional crests should not obstruct calendar text.
document.querySelectorAll('[data-cal-crest]').forEach(function(image) {
    image.addEventListener('error', function() { image.remove(); });
    if (image.complete && !image.naturalWidth) image.remove();
});

// Forecasts load independently so provider latency never holds up Home.
function initWeather() {
    var section = document.querySelector('[data-weather-url]');
    if (!section) return;
    var content = section.querySelector('[data-weather-content]');
    var lastRequest = 0;
    var loading = false;
    var refreshMs = 20 * 60 * 1000;
    function loadWeather() {
        if (loading) return;
        loading = true;
        lastRequest = Date.now();
        content.textContent = 'Loading weather and clothing cues…';
        content.setAttribute('aria-busy', 'true');
        var controller = new AbortController();
        var timeout = setTimeout(function() { controller.abort(); }, 8000);
        fetch(section.dataset.weatherUrl, { signal: controller.signal, credentials: 'same-origin' })
            .then(function(response) {
                if (!response.ok || !(response.headers.get('Content-Type') || '').includes('text/html')) {
                    throw new Error('Weather unavailable');
                }
                return response.text();
            })
            .then(function(html) { content.innerHTML = html; })
            .catch(function() {
                content.textContent = 'Weather could not load. Refresh the page to retry, or check a local forecast before heading out.';
            })
            .finally(function() {
                clearTimeout(timeout);
                loading = false;
                content.setAttribute('aria-busy', 'false');
            });
    }
    function refreshIfDue() {
        if (!document.hidden && Date.now() - lastRequest >= refreshMs) loadWeather();
    }
    loadWeather();
    setInterval(refreshIfDue, refreshMs);
    document.addEventListener('visibilitychange', refreshIfDue);
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWeather);
} else {
    initWeather();
}
