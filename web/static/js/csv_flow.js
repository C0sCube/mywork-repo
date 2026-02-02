// =====================================================
// PIPELINE UI CONTROLLER (CSV ↔ JSON ↔ ADMIN)
// =====================================================

// ---------------- DOM REFERENCES ----------------
const csvCard    = document.querySelector('[data-card="csv"]');
const jsonCard   = document.querySelector('[data-card="json"]');
const statusCard = document.querySelector('[data-card="status"]');

const csvInput   = document.getElementById("csvInput");
const jsonInput  = document.getElementById("inputJson");

const csvConvertBtn  = document.getElementById("csvConvertBtn");
const jsonConvertBtn = document.getElementById("jsnConvertBtn");
const csvDldBtn      = document.getElementById("csvDldBtn");
const jsonDldBtn     = document.getElementById("jsonDldBtn");
const jsonViewBtn    = document.getElementById("jsonViewBtn");
const jsonPushBtn    = document.getElementById("jsonPushBtn");

const csvTitle  = document.getElementById("csvTitle");
const jsonTitle = document.getElementById("jsonTitle");

const statusConsole = document.getElementById("statusConsole");

const csvOverlay  = csvCard.querySelector(".card-overlay");
const jsonOverlay = jsonCard.querySelector(".card-overlay");

// ---------------- UI HELPERS ----------------
function lockCard(card) {
  card.dataset.state = "locked";
  card.querySelectorAll("button,input").forEach(el => el.disabled = true);
}

function unlockCard(card) {
  card.dataset.state = "active";
  card.querySelectorAll("button,input").forEach(el => el.disabled = false);
}

function showOverlay(overlay, text) {
  overlay.classList.remove("hidden");
  if (text) overlay.querySelector(".overlay-text").textContent = text;
}

function hideOverlay(overlay) {
  overlay.classList.add("hidden");
}

function logStatus(msg) {
  statusConsole.textContent = msg;
}

// ---------------- PIPELINE STATE ----------------
const pipeline = {
  csv: null,       // File
  json: null,      // File
  csvName: null,   // string
  jsonName: null   // string
};

// =====================================================
// CSV → JSON
// =====================================================

// CSV upload
csvInput.addEventListener("change", () => {
  if (!csvInput.files.length) return;

  pipeline.csv = csvInput.files[0];
  csvTitle.textContent = pipeline.csv.name;
  csvConvertBtn.disabled = false;

  logStatus("CSV uploaded. Ready to convert.");
});

// CSV → JSON convert
csvConvertBtn.addEventListener("click", async () => {
  if (!pipeline.csv) return;

  lockCard(csvCard);
  lockCard(jsonCard);
  showOverlay(csvOverlay, "Converting CSV…");
  logStatus("Converting CSV → JSON…");

  const fd = new FormData();
  fd.append("csv", pipeline.csv);

  try {
    const res = await fetch("/convert_csv", {
      method: "POST",
      body: fd
    });

    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    pipeline.jsonName = data.json_file;
    jsonTitle.textContent = data.json_file;

    // JSON exists on server only
    jsonViewBtn.disabled = false;
    jsonPushBtn.disabled = false;

    // 🚫 JSON → CSV is NOT allowed here
    jsonConvertBtn.disabled = true;
    jsonInput.disabled = true;
    jsonDldBtn.disabled = true;

    unlockCard(jsonCard);
    logStatus("CSV → JSON done. Ready for Admin push.");

  } catch (err) {
    logStatus("Error: " + err.message);
  } finally {
    hideOverlay(csvOverlay);
  }
});

// =====================================================
// JSON ACTIONS (from CSV → JSON)
// =====================================================

// View JSON
jsonViewBtn.addEventListener("click", () => {
  if (!pipeline.jsonName) return;
  window.open(`/viewer/json/csv/${pipeline.jsonName}`, "_blank");
});

// Download JSON
jsonDldBtn.addEventListener("click", () => {
  if (!pipeline.jsonName) return;
  const path = `tmp/${pipeline.jsonName}`;
  window.location.href = `/download_json?path=${encodeURIComponent(path)}`;
});

// =====================================================
// JSON UPLOAD → JSON → CSV
// =====================================================

// JSON upload
jsonInput.addEventListener("change", () => {
  if (!jsonInput.files.length) return;

  pipeline.json = jsonInput.files[0];
  pipeline.jsonName = pipeline.json.name;
  jsonTitle.textContent = pipeline.json.name;

  lockCard(csvCard);           // CSV disabled
  unlockCard(jsonCard);

  jsonConvertBtn.disabled = false;
  jsonPushBtn.disabled = false;
  jsonViewBtn.disabled = false;

  logStatus("JSON uploaded. You can convert to CSV or push.");
});

// JSON → CSV
jsonConvertBtn.addEventListener("click", async () => {
  if (!pipeline.json) return;

  lockCard(jsonCard);
  showOverlay(jsonOverlay, "Converting JSON…");
  logStatus("Converting JSON → CSV…");

  const fd = new FormData();
  fd.append("json", pipeline.json);

  try {
    const res = await fetch("/convert_json", {
      method: "POST",
      body: fd
    });

    const ct = res.headers.get("content-type");
    if (!ct || !ct.includes("application/json")) {
      const text = await res.text();
      throw new Error(text.slice(0, 200));
    }

    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    pipeline.csvName = data.csv_file;
    csvTitle.textContent = data.csv_file;

    unlockCard(csvCard);
    csvDldBtn.disabled = false;
    csvConvertBtn.disabled = true;

    logStatus("JSON → CSV completed.");

  } catch (err) {
    logStatus("Error: " + err.message);
  } finally {
    hideOverlay(jsonOverlay);
  }
});

// CSV download
csvDldBtn.addEventListener("click", () => {
  if (!pipeline.csvName) return;
  const path = `tmp/${pipeline.csvName}`;
  window.location.href = `/download_csv?path=${encodeURIComponent(path)}`;
});

// =====================================================
// JSON → ADMIN PANEL
// =====================================================
jsonPushBtn.addEventListener("click", async () => {
  if (!pipeline.jsonName) return;

  lockCard(jsonCard);
  showOverlay(jsonOverlay, "Pushing to Admin…");
  logStatus("Pushing JSON to Admin Panel…");

  try {
    const res = await fetch("/push_json_sp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify({
        json_name: pipeline.jsonName
      })
    });

    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    logStatus("JSON pushed successfully.");

    // ✅ hide push button after success
    jsonPushBtn.disabled = true;
    jsonPushBtn.style.display = "none";

  } catch (err) {
    logStatus("Push error: " + err.message);
  } finally {
    hideOverlay(jsonOverlay);
  }
});



// =====================================================
// AUTH + NAV
// =====================================================
async function enforceAuth() {
  try {
    const r = await fetch("/auth-check");
    const d = await r.json();
    if (!d.logged_in) {
      alert("Session expired.");
      window.location = "/login";
    }
  } catch {
    window.location = "/login";
  }
}

function goBack(e) {
  e.preventDefault();
  window.location.href = "/";
}

document.addEventListener("DOMContentLoaded", () => {
  enforceAuth();

  // DEFAULT STATE
  unlockCard(csvCard);
  unlockCard(jsonCard);

  csvConvertBtn.disabled = true;
  jsonConvertBtn.disabled = true;
  csvDldBtn.disabled = true;
  jsonDldBtn.disabled = true;
  jsonPushBtn.disabled = true;
  jsonViewBtn.disabled = true;

  document
    .querySelectorAll("[data-action='back']")
    .forEach(el => el.addEventListener("click", goBack));
});

