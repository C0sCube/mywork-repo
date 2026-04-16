// ---------------- STATE ----------------
const jsonInput = document.getElementById("jsonInput");
const errorDisplay = document.getElementById("errorDisplay");
const yearSelect = document.getElementById("yearSelect");
const fileSelect = document.getElementById("fileSelect");
const years = ["2026", "2025", "2024", "2023", "sidkim", "0000", "0001"];

async function loadYears() {
    try {
        const res = await fetch("/years");
        const years = await res.json();

        yearSelect.innerHTML = "";

        if (!years.length) return;

        years.forEach((year, index) => {
            const opt = document.createElement("option");
            opt.value = year;
            opt.textContent = year;
            yearSelect.appendChild(opt);

            // set first as default
            if (index === 0) {
                yearSelect.value = year;
            }
        });

        // 🔥 trigger file loading after setting value
        await loadFileList();

    } catch (err) {
        console.error("Failed to load years:", err);
    }
}


// ---------------- INIT ----------------
document.addEventListener("DOMContentLoaded", () => {
    enforceAuth();

    loadYears(); // ← THIS is your entry point

    yearSelect.addEventListener("change", loadFileList);

    bindActions();
});

// ---------------- ACTION BINDINGS ----------------
function bindActions() {
    document.querySelectorAll("[data-action='back']")
        .forEach(el => el.addEventListener("click", goBackToMain));

    document.querySelector("[data-action='load']")?.addEventListener("click", loadConfig);
    document.querySelector("[data-action='save']")?.addEventListener("click", saveConfig);
    document.querySelector("[data-action='create']")?.addEventListener("click", createConfig);
    document.querySelector("[data-action='delete']")?.addEventListener("click", deleteConfig);
    document.querySelector("[data-action='backup']")?.addEventListener("click", backupConfig);
}

// ---------------- FILE LIST ----------------
async function loadFileList() {
    const year = yearSelect.value;
    const resp = await fetch(`/list-files/${year}`);
    const data = await resp.json();
    fileSelect.innerHTML = "";
    data.files.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f;
        opt.textContent = f;
        fileSelect.appendChild(opt);
    });
}


// ---------------- CRUD ----------------
async function loadConfig() {
    const year = yearSelect.value;
    const filename = fileSelect.value;
    const resp = await fetch("/load-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, filename })
    });
    const result = await resp.json();
    if (result.success) {
        jsonInput.value = JSON.stringify(result.data, null, 2);
        validateJSON();
    } else alert(result.error);
}

async function saveConfig() {
    if (!validateJSON()) return;
    const resp = await fetch("/save-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            year: yearSelect.value,
            filename: fileSelect.value,
            content: jsonInput.value
        })
    });
    const r = await resp.json();
    alert(r.success ? "Saved" : r.error);
}

async function createConfig() {
    const year = yearSelect.value;
    const name = prompt("Enter filename (without extension)");
    if (!name) return;
    const ext = prompt("json or json5", "json");
    const filename = `${name}.${ext}`;

    const r = await fetch("/create-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, filename })
    }).then(r => r.json());

    alert(r.success ? "Created" : r.error);
    loadFileList();
}

async function deleteConfig() {
    if (!confirm("Delete selected file?")) return;
    const r = await fetch("/delete-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            year: yearSelect.value,
            filename: fileSelect.value
        })
    }).then(r => r.json());

    alert(r.success ? "Deleted" : r.error);
    jsonInput.value = "";
    loadFileList();
}

async function backupConfig() {
    const r = await fetch("/backup-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            year: yearSelect.value,
            filename: fileSelect.value
        })
    }).then(r => r.json());

    alert(r.success ? "Backup done" : r.message);
}

// ---------------- VALIDATION ----------------
function validateJSON() {
    try {
        JSON.parse(jsonInput.value);
        errorDisplay.textContent = "";
        return true;
    } catch {
        try {
            JSON5.parse(jsonInput.value);
            errorDisplay.textContent = "";
            return true;
        } catch (e) {
            errorDisplay.textContent = e.message;
            return false;
        }
    }
}


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
