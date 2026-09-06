// =====================================================
// PIPELINE UI CONTROLLER (CSV ↔ JSON ↔ ADMIN)
// =====================================================

// ---------------- DOM REFERENCES ----------------
const csvCard = document.querySelector('[data-card="csv"]');
const jsonCard = document.querySelector('[data-card="json"]');
const statusCard = document.querySelector('[data-card="status"]');

const csvInput = document.getElementById("csvInput");
const jsonInput = document.getElementById("inputJson");

const csvConvertBtn = document.getElementById("csvConvertBtn");
const jsonConvertBtn = document.getElementById("jsnConvertBtn");
const csvDldBtn = document.getElementById("csvDldBtn");
const jsonDldBtn = document.getElementById("jsonDldBtn");
const jsonViewBtn = document.getElementById("jsonViewBtn");
const jsonPushBtn = document.getElementById("jsonPushBtn");

const exitBtn = document.getElementById("exitBtn");

const csvTitle = document.getElementById("csvTitle");
const jsonTitle = document.getElementById("jsonTitle");

const statusConsole = document.getElementById("statusConsole");

const csvOverlay = csvCard ? csvCard.querySelector(".card-overlay") : null;
const jsonOverlay = jsonCard ? jsonCard.querySelector(".card-overlay") : null;

// ---------------- UI HELPERS ----------------
function logStatus(msg) {
  if (statusConsole) statusConsole.textContent = msg;
}

function lockCard(card) {
  if (!card) return;
  card.dataset.state = "locked";
  card.querySelectorAll("button,input").forEach(el => el.disabled = true);
}

function unlockCard(card) {
  if (!card) return;
  card.dataset.state = "active";
  card.querySelectorAll("button,input").forEach(el => el.disabled = false);
}

function showOverlay(overlay, text) {
  if (!overlay) return;
  overlay.classList.remove("hidden");
  if (text) overlay.querySelector(".overlay-text").textContent = text;
}

function hideOverlay(overlay) {
  if (!overlay) return;
  overlay.classList.add("hidden");
}

function disable(el, val = true) {
  if (el) el.disabled = val;
}

// ---------------- PIPELINE STATE ----------------
const pipeline = {
  csvFile: null,     // File
  jsonFile: null,    // File (only when uploaded directly)
  csvName: null,     // server-side CSV name
  jsonName: null,    // server-side JSON name
  jsonSource: null   // "upload" | "csv"
};

// =====================================================
// CSV → JSON
// =====================================================
if (csvInput) {
  csvInput.addEventListener("change", () => {
    if (!csvInput.files.length) return;

    pipeline.csvFile = csvInput.files[0];
    csvTitle && (csvTitle.textContent = pipeline.csvFile.name);
    disable(csvConvertBtn, false);

    logStatus("CSV uploaded. Ready to convert.");
  });
}

if (csvConvertBtn) {
  csvConvertBtn.addEventListener("click", async () => {
    if (!pipeline.csvFile) return;

    lockCard(csvCard);
    lockCard(jsonCard);
    showOverlay(csvOverlay, "Converting CSV…");
    logStatus("Converting CSV → JSON…");

    const fd = new FormData();
    fd.append("csv", pipeline.csvFile);

    try {
      const res = await fetch("/convert_csv", { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      pipeline.jsonName = data.json_file;
      pipeline.jsonSource = "csv";
      pipeline.jsonFile = null;

      jsonTitle && (jsonTitle.textContent = pipeline.jsonName);

      disable(jsonViewBtn, false);
      disable(jsonPushBtn, false);
      disable(jsonConvertBtn, true);
      disable(jsonInput, true);
      disable(jsonDldBtn, false);

      unlockCard(jsonCard);
      logStatus("CSV → JSON done. Ready for Admin push.");

    } catch (err) {
      logStatus("❌ " + err.message);
    } finally {
      hideOverlay(csvOverlay);
    }
  });
}

// =====================================================
// JSON VIEW
// =====================================================
if (jsonViewBtn) {
  jsonViewBtn.addEventListener("click", () => {
    if (!pipeline.jsonName) return;
    window.open(`/viewer/json/csv/${pipeline.jsonName}`, "_blank");
  });
}

if (jsonDldBtn) {
  jsonDldBtn.addEventListener("click", () => {
    if (!pipeline.jsonName) return;

    window.location.href =
      `/download_pipeline_json/${encodeURIComponent(pipeline.jsonName)}`;
  });
}



// =====================================================
// JSON UPLOAD → JSON → CSV
// =====================================================
if (jsonInput) {
  jsonInput.addEventListener("change", () => {
    if (!jsonInput.files.length) return;

    pipeline.jsonFile = jsonInput.files[0];
    pipeline.jsonName = pipeline.jsonFile.name;
    pipeline.jsonSource = "upload";

    jsonTitle && (jsonTitle.textContent = pipeline.jsonName);

    lockCard(csvCard);
    unlockCard(jsonCard);

    disable(jsonConvertBtn, false);
    disable(jsonPushBtn, false);
    disable(jsonViewBtn, false);

    logStatus("JSON uploaded. You can convert to CSV or push.");
  });
}

if (jsonConvertBtn) {
  jsonConvertBtn.addEventListener("click", async () => {
    if (!pipeline.jsonFile) return;

    lockCard(jsonCard);
    showOverlay(jsonOverlay, "Converting JSON…");
    logStatus("Converting JSON → CSV…");

    const fd = new FormData();
    fd.append("json", pipeline.jsonFile);

    try {
      const res = await fetch("/convert_json", { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      pipeline.csvName = data.csv_file;
      csvTitle && (csvTitle.textContent = pipeline.csvName);

      unlockCard(csvCard);
      disable(csvDldBtn, false);
      disable(csvConvertBtn, true);

      logStatus("JSON → CSV completed.");

    } catch (err) {
      logStatus("❌ " + err.message);
    } finally {
      hideOverlay(jsonOverlay);
    }
  });
}

if (csvDldBtn) {
  csvDldBtn.addEventListener("click", () => {
    if (!pipeline.csvName) return;
    window.location.href = `/download_csv/${encodeURIComponent(pipeline.csvName)}`;
  });
}

// =====================================================
// JSON → ADMIN PANEL
// =====================================================
if (jsonPushBtn) {
  jsonPushBtn.addEventListener("click", async () => {
    lockCard(jsonCard);
    showOverlay(jsonOverlay, "Pushing to Admin…");
    logStatus("Pushing JSON to Admin Panel…");
    console.log("Pushing JSON to Admin Panel…");
    try {
      const fd = new FormData();

      if (pipeline.jsonSource === "csv") {
        fd.append("json_name", pipeline.jsonName);
      } else {
        fd.append("json", pipeline.jsonFile);
      }

      const res = await fetch("/push_json_sp", { method: "POST", body: fd });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      logStatus("✅ JSON pushed successfully.");
      // console.log("✅ JSON pushed successfully.");
      disable(jsonPushBtn, true);
      jsonPushBtn.style.display = "none";

    } catch (err) {
      logStatus("❌ Push error: " + err.message);
      console.log(err);
    } finally {
      hideOverlay(jsonOverlay);
    }
  });
}

// =====================================================
// AUTH
// =====================================================
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

document.addEventListener("DOMContentLoaded", () => {
  enforceAuth();

  unlockCard(csvCard);
  unlockCard(jsonCard);

  disable(csvConvertBtn, true);
  disable(jsonConvertBtn, true);
  disable(csvDldBtn, true);
  disable(jsonPushBtn, true);
  disable(jsonViewBtn, true);

  document.querySelectorAll("[data-action='back']").forEach(el => {
    el.addEventListener("click", async () => {
      await fetch("/cleanup_pipeline", { method: "POST" });
      goBackToMain();
    });
  });
});