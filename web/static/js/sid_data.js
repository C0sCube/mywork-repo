/* =========================================================
   SID / KIM DATA PAGE — FULL JS
   ========================================================= */

/* ================= DOM ================= */

const pdfInput     = document.getElementById("sidPdfInput");
const uploadBox    = document.getElementById("uploadBox");
const pdfViewer    = document.getElementById("pdfViewer");
const processBtn   = document.getElementById("sidProcessBtn");
const grid         = document.querySelector(".sid-input-grid");

// fields
const field1 = document.getElementById("field-1");
const field2 = document.getElementById("field-2");
const field3 = document.getElementById("field-3");

const input1 = document.getElementById("input1");
const input2 = document.getElementById("input2");
const input3 = document.getElementById("input3");

const label1 = document.getElementById("label1");
const label2 = document.getElementById("label2");
const label3 = document.getElementById("label3");

/* ================= STATE ================= */

let currentMode = null;   // "SID" | "KIM" | null
let currentFile = null;

/* ================= INIT ================= */

processBtn.disabled = true;

/* ================= PDF UPLOAD ================= */

pdfInput.addEventListener("change", () => {
  const file = pdfInput.files?.[0];
  if (!file) return;

  currentFile = file;

  // swap UI
  uploadBox.hidden = true;
  pdfViewer.hidden = false;
  pdfViewer.src = URL.createObjectURL(file);

  // configure inputs based on filename
  configureInputsFromFilename(file.name);
});

/* ================= MODE CONFIG ================= */

function configureInputsFromFilename(filename) {
  const name = filename.toUpperCase();

  resetInputs();
  grid.classList.remove("sid-mode", "kim-mode");

  if (name.endsWith("_SID.PDF")) {
    currentMode = "SID";
    configureSID();

  } else if (name.endsWith("_KIM.PDF")) {
    currentMode = "KIM";
    configureKIM();

  } else {
    currentMode = null;
    configureFallback();
  }

  validateInputs();
}

/* ---------- SID MODE ---------- */

function configureSID() {
  grid.classList.add("sid-mode");

  field1.classList.remove("hidden");
  field2.classList.remove("hidden");
  field3.classList.remove("hidden");

  label1.textContent = "First Page";
  label2.textContent = "Table Data";
  label3.textContent = "Manager Page";
}

/* ---------- KIM MODE ---------- */

function configureKIM() {
  grid.classList.add("kim-mode");

  field1.classList.remove("hidden");
  field2.classList.remove("hidden");
  field3.classList.add("hidden"); // 🚫 no third input

  label1.textContent = "Instrument Page";
  label2.textContent = "Instrument Count";
}

/* ---------- FALLBACK ---------- */

function configureFallback() {
  grid.classList.add("kim-mode");

  field1.classList.remove("hidden");
  field2.classList.remove("hidden");
  field3.classList.add("hidden");

  label1.textContent = "Field 1";
  label2.textContent = "Field 2";
}

/* ================= INPUT RESET ================= */

function resetInputs() {
  [input1, input2, input3].forEach(i => {
    i.value = "";
  });

  field3.classList.remove("hidden");
}

/* ================= VALIDATION ================= */

function validateInputs() {
  if (!currentFile || pdfViewer.hidden) {
    processBtn.disabled = true;
    return;
  }

  const visibleInputs = [
    ...grid.querySelectorAll(".sid-field:not(.hidden) input")
  ];

  const allFilled = visibleInputs.every(
    i => i.value.trim().length > 0
  );

  processBtn.disabled = !allFilled;
}

document
  .querySelectorAll(".sid-field input")
  .forEach(i => i.addEventListener("input", validateInputs));

/* ================= PROCESS ================= */

processBtn.addEventListener("click", () => {
  if (processBtn.disabled) return;

  const payload = buildPayload();

  console.log("SID/KIM PROCESS PAYLOAD", payload);

  alert(
    `${currentMode} processing triggered.\n\n` +
    JSON.stringify(payload, null, 2)
  );

  // 🔌 Next step: POST this payload to backend
});

/* ================= PAYLOAD BUILDER ================= */

function buildPayload() {
  const base = {
    filename: currentFile?.name || "",
    mode: currentMode
  };

  if (currentMode === "SID") {
    return {
      ...base,
      scheme_front_name: input1.value.trim(),
      sid_data: input2.value.trim(),
      manager: input3.value.trim()
    };
  }

  if (currentMode === "KIM") {
    return {
      ...base,
      page: input1.value.trim(),
      instrument_count: input2.value.trim()
    };
  }

  return base;
}


// ---------------- NAVIGATION ----------------
async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");
        const data = await r.json();

        if (!data.logged_in) {
            alert("Session expired. Please log in again.");
            window.location = "/login";
        }
    } catch (err) {
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


    document.querySelectorAll("[data-action='back']").forEach(el => {
        el.addEventListener("click", goBackToMain);
    });
});
