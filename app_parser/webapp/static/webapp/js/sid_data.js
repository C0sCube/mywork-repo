/* =========================================================
   SID / KIM DATA PAGE
   ========================================================= */

/* ================= DOM ================= */

const pdfInput = document.getElementById("sidPdfInput");
const uploadSection = document.getElementById("uploadSection");
const pdfViewer = document.getElementById("pdfViewer");
const processBtn = document.getElementById("sidProcessBtn");
const actionFooter = document.getElementById("actionFooter");
const grid = document.querySelector(".sid-input-grid");

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

let currentMode = null;
let currentFile = null;

/* ================= INIT ================= */

processBtn.disabled = true;

/* ================= PDF UPLOAD ================= */

pdfInput.addEventListener("change", () => {
    const file = pdfInput.files?.[0];
    if (!file) return;

    currentFile = file;

    uploadSection.hidden = true;
    pdfViewer.hidden = false;
    pdfViewer.src = URL.createObjectURL(file);

    actionFooter.hidden = false;

    configureFromFilename(file.name);
});

/* ================= MODE CONFIG ================= */

function configureFromFilename(filename) {
    const name = filename.toUpperCase();

    resetInputs();
    hideAllFields();

    currentMode = null;

    if (name.endsWith("_SID.PDF")) {
        currentMode = "SID";
        setupSID();
    } else if (name.endsWith("_KIM.PDF")) {
        currentMode = "KIM";
        setupKIM();
    } else {
        setupFallback();
    }

    validateInputs();
}

/* ---------- SID MODE ---------- */

function setupSID() {
    show(field1);
    show(field2);
    show(field3);

    enableInputs();

    label1.textContent = "Front Page";
    label2.textContent = "Data Page";
    label3.textContent = "Manager Page";
}

/* ---------- KIM MODE ---------- */

function setupKIM() {
    show(field1);
    show(field2);
    hide(field3);

    label1.textContent = "Instrument Page";
    label2.textContent = "Instrument Count";
}

/* ---------- FALLBACK ---------- */

function setupFallback() {
    show(field1);
    show(field2);
    hide(field3);

    label1.textContent = "Field 1";
    label2.textContent = "Field 2";
}

/* ================= HELPERS ================= */

function show(el) {
    el.classList.remove("hidden");
}
function hide(el) {
    el.classList.add("hidden");
}

function hideAllFields() {
    hide(field1);
    hide(field2);
    hide(field3);
}

function resetInputs() {
    input1.value = "";
    input2.value = "";
    input3.value = "";
}

function enableInputs() {
  input1.disabled = false;
  input2.disabled = false;
  input3.disabled = false;
}


/* ================= VALIDATION ================= */

function validateInputs() {
    if (!currentFile || !currentMode) {
        processBtn.disabled = true;
        return;
    }

    const visibleInputs = [
        ...grid.querySelectorAll(".sid-field:not(.hidden) input")
    ];

    const allFilled = visibleInputs.every(
        input => input.value.trim().length > 0
    );

    processBtn.disabled = !allFilled;
}

document
    .querySelectorAll(".sid-field input")
    .forEach(input =>
        input.addEventListener("input", validateInputs)
    );

/* ================= PROCESS ================= */

processBtn.addEventListener("click", async () => {
    if (processBtn.disabled) return;

    const meta = buildPayload();

    const fd = new FormData();
    fd.append("pdf", currentFile);
    fd.append("meta", JSON.stringify(meta));

    processBtn.disabled = true;
    processBtn.textContent = "Uploading...";

    try {
        const res = await fetch("/upload-sid-kim", {
            method: "POST",
            body: fd
        });

        const data = await res.json();

        if (!data.success) {
            throw new Error(data.error || "Upload failed");
        }

        alert("PDF queued successfully for processing");
        location.reload();

    } catch (err) {
        alert(err.message);
        processBtn.disabled = false;
        processBtn.textContent = "Process";
    }
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
            front_page: input1.value.trim(),
            data_page: input2.value.trim(),
            manager_page: input3.value.trim()
        };
    }

    if (currentMode === "KIM") {
        return {
            ...base,
            instr_page: input1.value.trim(),
            instr_count: input2.value.trim()
        };
    }

    return base;
}

/* ================= AUTH ================= */

async function enforceAuth() {
    try {
        const response = await fetch("/auth-check");

        if (!response.ok) {
            window.location = "/login";
            return;
        }

        const data = await response.json();

        if (!data.logged_in) {
            window.location = "/login";
        }
    } catch {
        window.location = "/login";
    }
}

/* ================= NAV ================= */

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
    document.querySelectorAll("[data-action='back']").forEach(el => {
        el.addEventListener("click", goBackToMain);
    });
});
