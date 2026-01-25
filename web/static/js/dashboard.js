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

        table.innerHTML = `
      <tr>
        <th>#</th><th>File</th><th>Processed</th>
        <th>Status</th><th>User</th><th>Error</th>
        <th>JSON</th><th>CSV</th><th>Reprocess</th><th>Push</th>
      </tr>`;

        data.rows.forEach((row, i) => {
            const tr = document.createElement("tr");
            const jsonName = row.file_name.replace(".pdf", ".json");
            const canPush = !!row.json_path;
            tr.innerHTML = `
                <td>${(currentPage - 1) * pageSize + index + 1}</td>
                <td> <a href="/viewer/pdf/${row.file_name}" target="_blank" class="menu__link">${row.file_name}</a></td>
                <td>${formatUTCDate(row.end_time) || "-"}</td>
                <td class="${statusClass(row.status)}">${row.status || "-"}</td>
                <td>${row.uploaded_by}</td>
                <td>${row.error || "-"}</td>
                <td>${row.json_path? `<a href="/viewer/json/${row.file_name.replace(".pdf", ".json")}" target="_blank">JSON</a>` : "-"} </td>
                <td> ${row.json_path? `<a href="/download_csv?path=${encodeURIComponent(row.json_path)}" target="_blank"><span class="material-symbols-outlined">docs</span> </a>` : "-" } </td>
                <td> ${canPush? `<button class="icon-btn" data-action="push" data-job="${row.id}"> <span class="material-symbols-outlined">publish</span> </button>`: "-" } </td>
                <td><button class="icon-btn" onclick="confirmReprocess('${row.file_name}')" title="Reprocess"><span class="material-symbols-outlined">autorenew</span> </button> </td>
                `;
            table.appendChild(tr);
        });

        logsConsole.innerHTML = "";
        logsConsole.appendChild(table);
    } catch {
        logsConsole.innerHTML = "<p>Error loading logs.</p>";
    }
}


// ================ PUSH ACTIONS ======================

document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-action='push']");
  if (!btn) return;

  const jobId = btn.dataset.job;
  if (!jobId) return;

  if (!confirm("Push this JSON to Admin Panel?")) return;

  btn.disabled = true;

  try {
    const resp = await fetch(`/push_job/${jobId}`, {
      method: "POST"
    });

    const data = await resp.json();

    if (data.success) {
      alert("Pushed to Admin Panel successfully.");
      loadLogs();
    } else {
      alert(data.error || "Push failed.");
    }
  } catch (err) {
    alert("Failed to push job.");
  } finally {
    btn.disabled = false;
  }
});
