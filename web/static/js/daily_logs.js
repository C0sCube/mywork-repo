let currentDate = null;
const logSelect = document.getElementById("LogSelect")
const logType = [
    "weblog","fslog"
]


// ---------------- LOG LOADING ----------------
async function loadLog() {
    const date = document.getElementById("dateSelect").value;

    

    if (!logSelect) {
        alert("Please select a log type: WEB or PARSER");
        return;
    }

    if (!date) {
        alert("Please select a date first.");
        return;
    }

    currentDate = date;
    const resp = await fetch("/load-daily-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date , logSelect})
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
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;

  const action = btn.dataset.action;

  switch (action) {
    case "json":
      window.open("/files/json/", "_blank");
      break;

    case "report":
      window.open("/files/xlsx/", "_blank");
      break;

    case "load":
      loadLog();
      break;

    case "refresh":
      refreshLog();
      break;

    case "back":
      goBackToMain();
      break;
  }
});

document.addEventListener("DOMContentLoaded", () => {
  enforceAuth();

  logType.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    logSelect.appendChild(opt);
  });


  // default to today
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dd = String(today.getDate()).padStart(2, "0");

  document.getElementById("dateSelect").value = `${yyyy}-${mm}-${dd}`;

  document.getElementById("logViewer")
    ?.addEventListener("scroll", syncScroll);

  loadLog();

   document
    .querySelectorAll("[data-action='back']")
    .forEach(el => el.addEventListener("click", goBackToMain));
});


// ---------------- AUTH ----------------
async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");

        if (!r.ok) {
            window.location = "/login";
            return;
        }

        const data = await r.json();

        if (!data.logged_in) {
            window.location = "/login";
        }

    } catch (err) {
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
   window.location.href = "/dashboard";
  }
}
