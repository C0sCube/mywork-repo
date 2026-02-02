// =====================================================
// PIPELINE UI CONTROLLER (CSV → JSON → PANEL)
// =====================================================

// ---------------- DOM REFERENCES ----------------
const csvCard    = document.querySelector('[data-card="csv"]');
const jsonCard   = document.querySelector('[data-card="json"]');
const statusCard = document.querySelector('[data-card="status"]');

const csvInput   = document.getElementById("csvInput");
const jsonInput  = document.getElementById("inputJson");

const csvBtn     = document.getElementById("csvConvertBtn");
const jsonPushBtn = document.getElementById("jsonPushBtn");
const jsonViewBtn = document.getElementById("jsonViewBtn");

const csvTitle  = document.getElementById("csvTitle");
const jsonTitle = document.getElementById("jsonTitle");

const statusConsole = document.getElementById("statusConsole");

const csvOverlay  = csvCard.querySelector(".card-overlay");
const jsonOverlay = jsonCard.querySelector(".card-overlay");

// ---------------- LOADER (KEPT + CLEANED) ----------------
const bar = document.querySelector(".bar");
const checks = document.querySelectorAll(".check");

function resetLoader() {
  if (!bar) return;
  bar.style.width = "0%";
  checks.forEach(c => {
    c.style.transform = "scale(0.75)";
    c.style.backgroundColor = "#535353";
  });
}

function reachCheckpoint(step) {
  if (!bar) return;

  if (step === 1) {
    bar.style.width = "50%";
    checks[0]?.style.setProperty("transform", "scale(1)");
    checks[0]?.style.setProperty("backgroundColor", "rgb(0,205,0)");
  }

  if (step === 2) {
    bar.style.width = "100%";
    checks[1]?.style.setProperty("transform", "scale(1)");
    checks[1]?.style.setProperty("backgroundColor", "rgb(0,205,0)");
  }
}

// ---------------- UI HELPERS ----------------
function lockCard(card) {
  card.dataset.state = "locked";
}

function unlockCard(card) {
  card.dataset.state = "active";
}

function showOverlay(overlay, text) {
  overlay.classList.remove("hidden");
  if (text) overlay.querySelector(".overlay-text").textContent = text;
}

function hideOverlay(overlay) {
  overlay.classList.add("hidden");
}

function logStatus(text) {
  statusConsole.textContent = text;
}

// ---------------- PIPELINE STATE ----------------
const pipeline = {
  csv: {
    file: null,
    uploaded: false
  },
  json: {
    file: null,
    ready: false
  }
};

// =====================================================
// CSV → JSON FLOW
// =====================================================

// CSV selected
csvInput.addEventListener("change", () => {
  if (!csvInput.files.length) return;

  pipeline.csv.file = csvInput.files[0];
  csvTitle.textContent = pipeline.csv.file.name;
  csvBtn.disabled = false;

  logStatus("CSV selected. Ready to convert.");
});

// Convert CSV → JSON
csvBtn.addEventListener("click", async () => {
  if (!pipeline.csv.file) return;

  resetLoader();
  lockCard(csvCard);
  showOverlay(csvOverlay, "Converting CSV…");

  logStatus("Converting CSV → JSON…");

  const fd = new FormData();
  fd.append("csv", pipeline.csv.file);

  let response;
  try {
    const res = await fetch("/convert_csv", {
      method: "POST",
      body: fd
    });
    response = await res.json();
  } catch (err) {
    hideOverlay(csvOverlay);
    logStatus("Network error during conversion.");
    return;
  }

  hideOverlay(csvOverlay);

  if (!response.success) {
    logStatus(response.error || "Conversion failed.");
    return;
  }

  // ✅ CSV → JSON checkpoint
  reachCheckpoint(1);

  pipeline.json.file = response.json_file;
  pipeline.json.ready = true;

  jsonTitle.textContent = pipeline.json.file;
  unlockCard(jsonCard);

  jsonViewBtn.disabled = false;
  jsonPushBtn.disabled = false;

  logStatus("CSV converted successfully. JSON ready.");
});

// =====================================================
// JSON ACTIONS
// =====================================================

// View JSON
jsonViewBtn.addEventListener("click", () => {
  if (!pipeline.json.file) {
    alert("No JSON available yet.");
    return;
  }

  window.open(`/viewer/json/csv/${pipeline.json.file}`, "_blank");
});

// Push JSON to Admin Panel
// Push JSON to Admin Panel
jsonPushBtn.addEventListener("click", async () => {
  if (!pipeline.json.ready) return;

  showOverlay(jsonOverlay, "Pushing to Admin Panel…");
  logStatus("Pushing JSON to Admin Panel…");

  try {
    const res = await fetch(`/push_job/${jobId}`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Accept": "application/json"
      }
    });

    const contentType = res.headers.get("content-type");

    // ✅ CRITICAL SAFETY CHECK
    if (!contentType || !contentType.includes("application/json")) {
      const text = await res.text();
      throw new Error(
        `Server returned non‑JSON (${res.status}): ${text.slice(0, 200)}`
      );
    }

    const response = await res.json();

    if (!res.ok || !response.success) {
      throw new Error(response.error || "Push failed.");
    }

    logStatus("JSON pushed successfully.");
    reachCheckpoint(2);

    setTimeout(() => location.reload(), 1500);

  } catch (err) {
    console.error(err);
    hideOverlay(jsonOverlay);
    logStatus("Push error: " + err.message);
  }
});

jsonInput.addEventListener("change", () => {
  if (!jsonInput.files.length) return;

  const file = jsonInput.files[0];

  // update pipeline
  pipeline.json.file = file.name;
  pipeline.json.ready = true;

  // UI updates
  jsonTitle.textContent = file.name;
  unlockCard(jsonCard);

  jsonViewBtn.disabled = false;
  jsonPushBtn.disabled = false;

  logStatus("JSON uploaded. Ready to push.");
});


// =====================================================
// AUTH + NAVIGATION (UNCHANGED, CLEANED)
// =====================================================

async function enforceAuth() {
  try {
    const r = await fetch("/auth-check");
    const data = await r.json();
    if (!data.logged_in) {
      alert("Session expired. Please log in again.");
      window.location = "/login";
    }
  } catch {
    alert("Unable to verify session. Redirecting to login.");
    window.location = "/login";
  }
}

function goBackToMain(e) {
  e.preventDefault();
  if (window.opener) {
    window.opener.focus();
    window.close();
  } else {
    window.location.href = "/";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  enforceAuth();

  document
    .querySelectorAll("[data-action='back']")
    .forEach(el => el.addEventListener("click", goBackToMain));
});
