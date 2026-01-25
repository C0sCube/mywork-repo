let currentDate = null;

// ---------------- AUTH ----------------
async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");
        const data = await r.json();

        if (!data.logged_in) {
            alert("Session expired. Log in again.");
            window.location = "/login";
        }
    } catch {
        alert("Unable to verify session. Redirecting to login.");
        window.location = "/login";
    }
}

// ---------------- NAV ----------------
function goBackToMain(e) {
    e.preventDefault();

    if (window.opener) {
        window.opener.focus();
        window.close();
    } else {
        window.location.href = "/";
    }
}

// ---------------- LOG LOADING ----------------
async function loadLog() {
    const date = document.getElementById("dateSelect").value;
    if (!date) {
        alert("Please select a date first.");
        return;
    }

    currentDate = date;

    const resp = await fetch("/load-daily-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date })
    });

    const data = await resp.json();
    updateLogViewer(data.content || "No logs available for this date.");
}

function refreshLog() {
    if (!currentDate) {
        alert("Load a log first.");
        return;
    }
    loadLog();
}

// ---------------- VIEWER ----------------
function updateLogViewer(text) {
    const viewer = document.getElementById("logViewer");
    const lineBox = document.getElementById("lineNumbers");

    viewer.textContent = text;

    const lineCount = text.split("\n").length;
    let nums = "";
    for (let i = 1; i <= lineCount; i++) {
        nums += String(i).padStart(2, "0") + "\n";
    }
    lineBox.textContent = nums;

    requestAnimationFrame(() => {
        viewer.scrollTop = viewer.scrollHeight;
        lineBox.scrollTop = viewer.scrollTop;
    });
}

function syncScroll() {
    const viewer = document.getElementById("logViewer");
    const lineBox = document.getElementById("lineNumbers");
    lineBox.scrollTop = viewer.scrollTop;
}

// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    enforceAuth();

    // default to today
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    document.getElementById("dateSelect").value = `${yyyy}-${mm}-${dd}`;

    // bind buttons
    document.querySelector("[data-action='load']")
        ?.addEventListener("click", loadLog);

    document.querySelector("[data-action='refresh']")
        ?.addEventListener("click", refreshLog);

    document.querySelectorAll("[data-action='back']")
        .forEach(el => el.addEventListener("click", goBackToMain));

    document.getElementById("logViewer")
        ?.addEventListener("scroll", syncScroll);

    loadLog();
});
