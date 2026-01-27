/* ================= AUTH ================= */
(async function enforceAuth() {
    try {
        const r = await fetch("/auth-check");
        const data = await r.json();
        if (!data.logged_in) {
            alert("Session Expired. Log in Again.");
            window.location = "/login";
        }
    } catch {
        alert("Unable to verify. Redirecting to login.");
        window.location = "/login";
    }
})();

/* ================= GLOBAL STATE ================= */
let selectedFiles = [];
let amcRegistry = {};
let currentPage = 1;
const pageSize = 15;

/* ================= INIT ================= */
document.addEventListener("DOMContentLoaded", async () => {
    bindActions();
    await loadRegistry();
    await loadLogs();

    setInterval(() => {
        const auto = document.getElementById("autoRefresh");
        if (auto && auto.checked) loadLogs();
    }, 15000);
});

/* ================= ACTION BINDINGS ================= */
function bindActions() {
    document.querySelector("[data-action='open-upload']")
        ?.addEventListener("click", () => toggleModal(true));

    document.querySelector("[data-action='close-upload']")
        ?.addEventListener("click", () => toggleModal(false));

    document.querySelectorAll("[data-action='new-tab']")
        .forEach(a => a.addEventListener("click", openInNewTab));

    document.querySelector("[data-action='refresh-logs']")
        ?.addEventListener("click", loadLogs);

    const pdfInput = document.getElementById("pdfs");
    pdfInput?.addEventListener("change", onFileSelect);

    document.getElementById("uploadForm")
        ?.addEventListener("submit", uploadFiles);
}

/* ================= NAV ================= */
function openInNewTab(e) {
    e.preventDefault();
    window.open(e.currentTarget.href, "_blank");
}

/* ================= MODAL ================= */
function toggleModal(state) {
    const modal = document.getElementById("uploadModal");
    if (!modal) return;
    state ? modal.classList.add("show") : modal.classList.remove("show");
}

/* ================= REGISTRY ================= */
async function loadRegistry() {
    try {
        const resp = await fetch("/company_registry");
        amcRegistry = await resp.json();
    } catch {
        amcRegistry = {};
    }
}

/* ================= FILE UPLOAD ================= */
function onFileSelect(e) {
    const sizeDiv = document.getElementById("sizeDisplay");
    const newFiles = Array.from(e.target.files);

    if (!newFiles.length) {
        sizeDiv.textContent = "Size 0 Mb / 50 Mb";
        return;
    }

    sizeDiv.textContent = "Selecting...";
    newFiles.forEach(f => {
        if (!selectedFiles.some(x => x.name === f.name && x.size === f.size)) {
            selectedFiles.push(f);
        }
    });

    updateUploadDisplay();
    e.target.value = "";
}

async function uploadFiles(ev) {
    ev.preventDefault();
    if (!selectedFiles.length) return alert("No files selected.");

    const consoleDiv = document.getElementById("uploadConsole");

    for (let i = 0; i < selectedFiles.length; i++) {
        const fd = new FormData();
        fd.append("pdfs", selectedFiles[i], selectedFiles[i].name);

        const row = consoleDiv.children[i];
        row.innerHTML = `<strong>Uploading… (${i + 1}/${selectedFiles.length})</strong>`;

        try {
            await fetch("/upload", { method: "POST", body: fd });
            row.innerHTML = `<span>${selectedFiles[i].name}</span> ✔`;
        } catch {
            row.innerHTML = `<span>${selectedFiles[i].name}</span> ❌`;
        }
    }

    alert("All uploads submitted.");
    window.location.reload();
}

function updateUploadDisplay() {
    const consoleDiv = document.getElementById("uploadConsole");
    const sizeDiv = document.getElementById("sizeDisplay");
    consoleDiv.innerHTML = "";

    let total = 0;
    selectedFiles.forEach((f, i) => {
        total += f.size;
        const d = document.createElement("div");
        d.className = "file-item";
        d.innerHTML = `
      <span>${f.name} (${(f.size / 1048576).toFixed(2)} MB)</span>
      <button class="remove-btn" onclick="removeFile(${i})">✖</button>
    `;
        consoleDiv.appendChild(d);
    });

    if (!selectedFiles.length) {
        consoleDiv.innerHTML = "<p>No files selected.</p>";
        sizeDiv.textContent = "Size 0 Mb / 50 Mb";
        return;
    }

    sizeDiv.textContent = `Size ${(total / 1048576).toFixed(2)} Mb / 50 Mb`;
}

/* ================= LOGS ================= */
async function loadLogs() {
    const logsConsole = document.getElementById("logsConsole");
    logsConsole.innerHTML = "<p>Refreshing…</p>";

    try {
        const resp = await fetch(`/status_data?page=${currentPage}&size=${pageSize}`);
        const data = await resp.json();

        if (!data.success || !data.rows.length) {
            logsConsole.innerHTML = "<p>No status yet.</p>";
            return;
        }

        const table = document.createElement("table");
        table.className = "status-table";

        //statusClass()
        table.innerHTML = `
      <tr>
        <th style = "width:40px;">#</th><th style = "width:200px;">File</th><th style = "width:140px;">Processed</th>
        <th style = "width:90px;">Status</th><th style = "width:160px;">User</th><th>Error</th>
        <th style = "width:50px;">JSON</th><th style = "width:50px;">CSV</th><th style = "width:80px;">Push</th><th style = "width:50px;">RePr</th>
      </tr>`;

        data.rows.forEach((row, i) => {
            const tr = document.createElement("tr");
            // const jsonName = row.file_name.replace(".pdf", ".json");
            // const canPush = !!row.json_path;

            const isPushed = row.status === "PUSHED";
            const pushCell = row.json_path
                ? `<label class="icon-btn switch"><span class="slider"><input type="checkbox" data-action="push-slider" data-job-id="${row.id}" ${isPushed ? "checked disabled" : ""}></span> </label>`: "-";

            
            tr.innerHTML = `
                <td>${(currentPage - 1) * pageSize + i + 1}</td>
                <td> <a href="/viewer/pdf/${row.file_name}" target="_blank" class="menu__link">${row.file_name}</a></td>
                <td>${formatUTCDate(row.end_time) || "-"}</td>
                <td class="${row.status}">${row.status || "-"}</td>
                <td>${row.uploaded_by}</td>
                <td>${row.error || "-"}</td>
                <td>${row.json_path ? `<a href="/viewer/json/${row.file_name.replace(".pdf", ".json")}" class ="menu__link" target="_blank" text-decoration: none>JSON</a>` : "-"} </td>
                <td> ${row.json_path ? `<a href="/download_csv?path=${encodeURIComponent(row.json_path)}" class ="menu__link" text-decoration: none><span class="material-symbols-outlined">docs</span> </a>` : ""} </td>
                <td>${pushCell}</td>
                <td><button class="icon-btn" onclick="confirmReprocess(${row.id})" title="Reprocess"><span class="material-symbols-outlined">autorenew</span></button></td>
                `;
            table.appendChild(tr);
        });

        logsConsole.innerHTML = "";
        logsConsole.appendChild(table);
    } catch (error) {
        console.log('errorrr>>>>>>>>>', error)
        logsConsole.innerHTML = "<p>Error loading logs.</p>";
    }
}


function formatUTCDate(dateString) {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString("en-GB", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "UTC" // force UTC
    });
}

function statusClass(status) {
    if (!status) return "";
    const s = status.toLowerCase();
    if (s === "completed") return "status-completed";
    if (s === "failed") return "status-failed";
    if (s === "pending") return "status-pending";
    return "";
} 

// ================ PUSH ACTIONS ======================

document.addEventListener("change", async (e) => {
    const checkbox = e.target;

    if (!checkbox.matches("[data-action='push-slider']")) return;

    const jobId = checkbox.dataset.jobId;

    /* only care about turning ON */
    if (!checkbox.checked) return;

    const ok = confirm(
        "This will push the JSON to Admin Panel.\n\nDo you want to continue?"
    );

    if (!ok) {
        checkbox.checked = false; // revert
        return;
    }

    checkbox.disabled = true;

    try {
        const resp = await fetch(`/push_job/${jobId}`, {
            method: "POST"
        });

        const data = await resp.json();

        if (!data.success) {
            alert(data.error || "Push failed.");
            checkbox.checked = false;
            checkbox.disabled = false;
            return;
        }

        // SUCCESS
        checkbox.checked = true;   // green
        checkbox.disabled = true;  // lock
        alert("Pushed to Admin Panel successfully.");
        await loadLogs(); 

    } catch (err) {
        alert("Network error while pushing.");
        // console.log(err);
        checkbox.checked = false;
        checkbox.disabled = false;
    }
});

// =========== reprocess ===========

async function confirmReprocess(filename) {
    const ok = confirm(
        `Reprocess this file?\n\n${filename}`
    );
    if (!ok) return;

    try {
        const resp = await fetch(
            `/reprocess/${encodeURIComponent(filename)}`,
            { method: "POST" }
        );

        const data = await resp.json();

        if (!data.success) {
            alert(data.message || "Reprocess failed.");
            return;
        }

        alert(data.message || "Reprocess queued.");

        // refresh the table so new job appears
        await loadLogs();

    } catch (err) {
        console.error(err);
        alert("Network error while reprocessing.");
    }
}
