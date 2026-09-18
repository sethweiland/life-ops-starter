var LANE_ORDER = {waiting_on_you: 0, blocked: 1, active: 2, idea: 3, parked: 4};
var LANE_LABELS = {
    idea: "Idea",
    active: "Active",
    blocked: "Blocked",
    waiting_on_you: "Waiting on you",
    parked: "Parked"
};
var laneFilter = "all";
var ownerFilter = "all";

function sortProjectList() {
    var list = document.querySelector(".project-list");
    if (!list) return;
    var rows = Array.prototype.slice.call(list.querySelectorAll(".project-row"));
    rows.sort(function(a, b) {
        var laneA = a.getAttribute("data-lane") || "";
        var laneB = b.getAttribute("data-lane") || "";
        var rank = (LANE_ORDER[laneA] != null ? LANE_ORDER[laneA] : 9) -
                   (LANE_ORDER[laneB] != null ? LANE_ORDER[laneB] : 9);
        if (rank !== 0) return rank;
        return (a.getAttribute("data-name") || "").localeCompare(b.getAttribute("data-name") || "", undefined, {sensitivity: "base"});
    });
    rows.forEach(function(row) { list.appendChild(row); });
}

function applyProjectFilters() {
    var rows = document.querySelectorAll(".project-row");
    var visible = 0;
    var selectedId = projectIdFromLocation();
    rows.forEach(function(row) {
        var laneOk = laneFilter === "all" || row.getAttribute("data-lane") === laneFilter;
        var owner = row.getAttribute("data-owner") || "";
        var ownerOk = ownerFilter === "all" || owner === ownerFilter;
        var selected = selectedId && row.getAttribute("data-id") === selectedId;
        var show = (laneOk && ownerOk) || selected;
        row.hidden = !show;
        if (show) visible += 1;
    });
    var empty = document.getElementById("project-empty-filter");
    if (empty) empty.hidden = visible !== 0 || rows.length === 0;
    var count = document.getElementById("project-count");
    if (count) {
        var total = rows.length;
        if (visible === total) {
            count.textContent = total + (total === 1 ? " project" : " projects");
        } else {
            count.textContent = "Showing " + visible + " of " + total;
        }
    }
}

function moveProjectLane(projectId, lane, selectEl) {
    var row = selectEl.closest('.project-row');
    var statusEl = document.getElementById("status-" + projectId);
    selectEl.disabled = true;
    fetch("/projects/api/projects/" + encodeURIComponent(projectId) + "/lane", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": lifeOpsCsrfToken() },
        body: JSON.stringify({ lane: lane })
    })
    .then(function(r) { return r.json().then(function(data) { return { ok: r.ok, data: data }; }); })
    .then(function(res) {
        if (res.data.success) {
            if (row) {
                row.setAttribute("data-lane", lane);
                var pill = row.querySelector('[data-role="status"]');
                if (pill) {
                    pill.textContent = LANE_LABELS[lane] || lane;
                    pill.className = "project-status lane-" + lane;
                }
            }
            sortProjectList();
            applyProjectFilters();
            if (statusEl) statusEl.textContent = "";
        } else if (statusEl) {
            statusEl.textContent = res.data.error || "Move failed";
        }
        selectEl.disabled = false;
    })
    .catch(function() {
        if (statusEl) statusEl.textContent = "Request failed";
        selectEl.disabled = false;
    });
}

document.querySelectorAll(".project-lane-select").forEach(function(selectEl) {
    selectEl.addEventListener("change", function() {
        moveProjectLane(selectEl.getAttribute("data-id"), selectEl.value, selectEl);
    });
});

function projectIdFromLocation() {
    var params = new URLSearchParams(window.location.search);
    var fromQuery = params.get("project");
    if (fromQuery) return fromQuery;
    var hash = (window.location.hash || "").replace(/^#/, "");
    if (!hash) return "";
    if (hash.indexOf("project-") === 0) return hash.slice("project-".length);
    return hash;
}

function selectDeepLinkedProject() {
    var projectId = projectIdFromLocation();
    document.querySelectorAll(".project-row.is-target").forEach(function(row) {
        row.classList.remove("is-target");
    });
    if (!projectId) return;
    var row = document.getElementById("project-" + projectId);
    if (!row) return;
    applyProjectFilters();
    row.classList.add("is-target");
    if (typeof row.scrollIntoView === "function") {
        row.scrollIntoView({ block: "center" });
    }
}

document.querySelectorAll(".project-chip").forEach(function(chip) {
    chip.addEventListener("click", function() {
        var kind = chip.getAttribute("data-filter");
        var value = chip.getAttribute("data-value");
        if (kind === "lane") laneFilter = value;
        if (kind === "owner") ownerFilter = value;
        document.querySelectorAll('.project-chip[data-filter="' + kind + '"]').forEach(function(other) {
            other.classList.toggle("is-active", other === chip);
        });
        applyProjectFilters();
    });
});

window.addEventListener("hashchange", selectDeepLinkedProject);
selectDeepLinkedProject();
